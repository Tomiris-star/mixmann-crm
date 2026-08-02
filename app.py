"""Учёт склада: локальный CSV в папке проекта или Google Sheets."""

from __future__ import annotations

import base64
import csv
import html
import io
import json
import os
import textwrap
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit_extras.dataframe_explorer import dataframe_explorer
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_option_menu import option_menu

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")
LOGO_PATH = APP_DIR / "assets" / "logo.png"
FAVICON_PATH = APP_DIR / "assets" / "favicon.png"
BRAND_CSS_PATH = APP_DIR / "static" / "mixmann.css"

SPREADSHEET_ID = os.getenv(
    "SPREADSHEET_ID",
    "1L4lZ9KUZUUJKpyGZx3YMv7dpIOlKRM3WcB5k0uqPAoc",
).strip()

# Необязательно: {"Склад": "0", "Операции": "123456"} — gid из URL листа (#gid=…)
_SHEET_GIDS_RAW = os.getenv("SHEET_GIDS", "").strip()
SHEET_GIDS: dict[str, str] = {}
if _SHEET_GIDS_RAW:
    try:
        parsed = json.loads(_SHEET_GIDS_RAW)
        if isinstance(parsed, dict):
            SHEET_GIDS = {str(k): str(v) for k, v in parsed.items()}
    except json.JSONDecodeError:
        pass

_credentials_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json").strip()
CREDENTIALS_FILE = Path(_credentials_path)
if not CREDENTIALS_FILE.is_absolute():
    CREDENTIALS_FILE = APP_DIR / CREDENTIALS_FILE

OAUTH_CLIENT_FILE = APP_DIR / "oauth_client.json"
TOKEN_FILE = APP_DIR / "authorized_user.json"

# local_csv | public_csv | service_account | oauth | auto
DATA_SOURCE = os.getenv("DATA_SOURCE", "local_csv").strip().casefold()

# public_csv | service_account | oauth | auto  (только при DATA_SOURCE != local_csv)
GOOGLE_AUTH = os.getenv("GOOGLE_AUTH", "public_csv").strip().casefold()

_LOCAL_CSV_ENV = os.getenv("LOCAL_CSV_FILE", "").strip()
DEFAULT_LOCAL_CSV_NAMES = (
    "МойСклад - Склад.csv",
    "МойСклад — Склад.csv",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

_PUBLIC_CSV_HINT = (
    "Таблица должна быть доступна по ссылке («Просмотр» или «Комментирование»). "
    "Данные скачиваются через публичный экспорт CSV — credentials.json не нужен."
)

_SERVICE_ACCOUNT_HINT = (
    "Положите JSON-ключ сервисного аккаунта в credentials.json (или задайте "
    "GOOGLE_SERVICE_ACCOUNT_FILE в .env) и откройте доступ к таблице для "
    "client_email из этого файла (роль «Читатель» или выше)."
)

TABS = {
    "Склад": "склад",
    "Операции": "Операции",
    "Расходы": "Расходы",
}

NAV_ITEMS: dict[str, dict[str, str]] = {
    "Склад": {"icon": "box-seam"},
    "Операции": {"icon": "cart-check"},
    "Расходы": {"icon": "wallet2"},
    "Настройки": {"icon": "gear"},
}

OPTION_MENU_STYLES: dict[str, dict[str, str]] = {
    "container": {"padding": "0!important", "background-color": "transparent"},
    "icon": {"color": "#0d9488", "font-size": "1.1rem"},
    "nav-link": {
        "font-size": "0.9rem",
        "font-family": "'Inter', system-ui, sans-serif",
        "font-weight": "500",
        "color": "#5c6778",
        "margin": "2px 0",
        "border-radius": "10px",
        "--hover-color": "rgba(13, 148, 136, 0.1)",
    },
    "nav-link-selected": {
        "background-color": "rgba(13, 148, 136, 0.12)",
        "color": "#1a2332",
        "font-weight": "600",
    },
}

EXPECTED_COLUMNS: dict[str, list[str]] = {
    "Склад": [
        "Категория",
        "Наименование",
        "Количество",
        "Ед. измерения",
        "Стоимость/Примечание",
    ],
}

WAREHOUSE_HEADER_ALIASES: dict[str, str] = {
    "тип": "Категория",
    "категория": "Категория",
    "наименование": "Наименование",
    "остаток": "Количество",
    "количество": "Количество",
    "ед. изм.": "Ед. измерения",
    "ед. измерения": "Ед. измерения",
    "единица измерения": "Ед. измерения",
    "средняя цена": "Стоимость/Примечание",
    "стоимость запасов": "Стоимость/Примечание",
    "стоимость/примечание": "Стоимость/Примечание",
    "примечание": "Стоимость/Примечание",
}

def _normalize_cell(value: object) -> str:
    return " ".join(str(value).replace("\xa0", " ").split())


def _resolve_local_csv_path() -> Path | None:
    if _LOCAL_CSV_ENV:
        path = Path(_LOCAL_CSV_ENV)
        if not path.is_absolute():
            path = APP_DIR / path
        return path if path.is_file() else None
    for name in DEFAULT_LOCAL_CSV_NAMES:
        path = APP_DIR / name
        if path.is_file():
            return path
    matches = sorted(APP_DIR.glob("*Склад*.csv"))
    return matches[0] if matches else None


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _fetch_sheet_local_csv(
    tab_key: str,
) -> tuple[list[list[str]], str, list[str]]:
    warnings: list[str] = []
    if tab_key != "Склад":
        warnings.append(
            f"Локальный CSV содержит только вкладку «Склад». "
            f"Для «{tab_key}» задайте DATA_SOURCE=public_csv (или API) в .env."
        )
        return [], TABS[tab_key], warnings

    path = _resolve_local_csv_path()
    if path is None:
        tried = ", ".join(DEFAULT_LOCAL_CSV_NAMES)
        raise FileNotFoundError(
            f"Файл склада не найден в {APP_DIR}. "
            f"Положите CSV (например {tried}) или задайте LOCAL_CSV_FILE в .env."
        )

    csv_text = _read_text_file(path)
    values = _csv_text_to_values(csv_text)
    if not values:
        raise LookupError(f"Файл {path.name} пустой.")
    return values, path.name, warnings


def _sheet_name_candidates(tab_key: str) -> list[str]:
    desired = TABS[tab_key]
    names = [desired, desired.casefold(), desired.title()]
    if tab_key == "Склад":
        names.extend(["Склад", "склад", "СКЛАД"])
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _resolve_auth_mode() -> str:
    if GOOGLE_AUTH in ("public_csv", "service_account", "oauth"):
        return GOOGLE_AUTH
    if CREDENTIALS_FILE.is_file():
        return "service_account"
    if OAUTH_CLIENT_FILE.is_file():
        return "oauth"
    return "public_csv"


def _load_oauth_client_dict() -> dict[str, Any] | None:
    if OAUTH_CLIENT_FILE.is_file():
        return json.loads(OAUTH_CLIENT_FILE.read_text(encoding="utf-8"))
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
    return None


def _load_authorized_user_dict() -> dict[str, Any] | None:
    if not TOKEN_FILE.is_file():
        return None
    data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _save_authorized_user(data: dict[str, Any]) -> None:
    TOKEN_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _public_csv_direct_export_url() -> str:
    """Публичный CSV всего документа / первого листа без gid."""
    return (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export"
        "?format=csv"
    )


def _public_csv_export_urls(tab_key: str) -> list[tuple[str, str]]:
    """URL публичного CSV и подпись листа (без gid — иначе часто HTTP 404)."""
    if not SPREADSHEET_ID:
        return []

    urls: list[tuple[str, str]] = []
    seen: set[str] = set()

    for name in _sheet_name_candidates(tab_key):
        url = (
            f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq"
            f"?tqx=out:csv&sheet={quote(name)}"
        )
        if url not in seen:
            seen.add(url)
            urls.append((url, name))

    direct = _public_csv_direct_export_url()
    if direct not in seen:
        urls.append((direct, "первый лист (export?format=csv)"))

    return urls


def _download_public_csv(url: str) -> str:
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; MixmannStock/1.0)"},
    )
    with urlopen(request, timeout=45) as response:
        raw = response.read()
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _csv_text_to_values(csv_text: str) -> list[list[str]]:
    frame = pd.read_csv(
        io.StringIO(csv_text),
        header=None,
        dtype=str,
        keep_default_na=False,
    )
    if frame.empty:
        return []
    return frame.fillna("").astype(str).values.tolist()


def _fetch_sheet_public_csv(
    tab_key: str,
) -> tuple[list[list[str]], str, list[str]]:
    warnings: list[str] = []
    desired = TABS[tab_key]
    candidates = _public_csv_export_urls(tab_key)
    if not candidates:
        raise LookupError("SPREADSHEET_ID не задан.")

    last_error: str | None = None
    for url, label in candidates:
        try:
            csv_text = _download_public_csv(url)
        except HTTPError as exc:
            last_error = f"HTTP {exc.code} для «{label}»"
            if exc.code in (401, 403):
                warnings.append(
                    f"Нет доступа к листу «{label}» ({exc.code}). {_PUBLIC_CSV_HINT}"
                )
            continue
        except URLError as exc:
            last_error = str(exc.reason or exc)
            continue

        stripped = csv_text.strip()
        if not stripped:
            last_error = f"Пустой ответ для «{label}»"
            continue
        if stripped.startswith("<!DOCTYPE") or stripped.startswith("<html"):
            last_error = f"Вместо CSV пришла HTML-страница для «{label}»"
            warnings.append(
                "Google вернул HTML вместо CSV — проверьте, что таблица открыта "
                "по ссылке для просмотра."
            )
            continue

        values = _csv_text_to_values(csv_text)
        if not values:
            last_error = f"Лист «{label}» пустой"
            continue

        is_direct_export = label.startswith("первый лист (export")
        resolved_title = desired if is_direct_export else label
        if (
            _normalize_cell(label).casefold() != _normalize_cell(desired).casefold()
            and not is_direct_export
        ):
            warnings.append(
                f"Лист загружен как «{label}» (в настройках указано «{desired}»)."
            )
        elif is_direct_export and tab_key != "Склад":
            warnings.append(
                f"Лист «{desired}» загружен через экспорт первого листа таблицы "
                f"(без gid). Если данные не те — переименуйте вкладку в Google Sheets "
                f"или включите доступ через API (credentials.json)."
            )
        return values, resolved_title, warnings

    raise LookupError(
        f"Не удалось скачать лист «{desired}» через публичный CSV. "
        f"{last_error or ''} {_PUBLIC_CSV_HINT}"
    )


@st.cache_resource(show_spinner="Подключение к Google Sheets…")
def get_gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials

    mode = _resolve_auth_mode()
    if mode == "public_csv":
        raise RuntimeError("gspread не используется при GOOGLE_AUTH=public_csv")
    if mode == "service_account":
        if not CREDENTIALS_FILE.is_file():
            raise FileNotFoundError(
                f"Файл ключа не найден: {CREDENTIALS_FILE}. {_SERVICE_ACCOUNT_HINT}"
            )
        creds = Credentials.from_service_account_file(
            str(CREDENTIALS_FILE),
            scopes=SCOPES,
        )
        return gspread.authorize(creds)

    oauth_client = _load_oauth_client_dict()
    if oauth_client is None:
        raise FileNotFoundError(
            f"Для OAuth нужен {OAUTH_CLIENT_FILE.name} или GOOGLE_CLIENT_ID/SECRET в .env."
        )
    authorized_user = _load_authorized_user_dict()
    client, updated_user = gspread.oauth_from_dict(
        credentials=oauth_client,
        authorized_user_info=authorized_user,
        scopes=SCOPES,
    )
    if updated_user:
        _save_authorized_user(updated_user)
    return client


def _open_spreadsheet(client):
    import gspread
    from gspread.exceptions import APIError, SpreadsheetNotFound

    try:
        return client.open_by_key(SPREADSHEET_ID)
    except SpreadsheetNotFound as exc:
        raise LookupError(
            f"Таблица {SPREADSHEET_ID} недоступна. Проверьте SPREADSHEET_ID и доступ "
            f"учётной записи API. {_SERVICE_ACCOUNT_HINT}"
        ) from exc
    except APIError as exc:
        raise LookupError(
            f"Google Sheets API: {exc}. {_SERVICE_ACCOUNT_HINT}"
        ) from exc


def _resolve_worksheet(spreadsheet, tab_key: str):
    from gspread.exceptions import WorksheetNotFound

    warnings: list[str] = []
    desired = TABS[tab_key]
    last_error: str | None = None

    gid = SHEET_GIDS.get(tab_key) or SHEET_GIDS.get(desired)
    if gid:
        try:
            worksheet = spreadsheet.get_worksheet_by_id(int(gid))
            if worksheet is not None:
                return worksheet, worksheet.title, warnings
        except (ValueError, WorksheetNotFound) as exc:
            last_error = str(exc)
            warnings.append(f"Лист по gid={gid} не найден ({exc}). Пробуем по имени…")

    for name in _sheet_name_candidates(tab_key):
        try:
            worksheet = spreadsheet.worksheet(name)
            if _normalize_cell(name).casefold() != _normalize_cell(desired).casefold():
                warnings.append(
                    f"Лист загружен как «{name}» (в настройках указано «{desired}»)."
                )
            return worksheet, name, warnings
        except WorksheetNotFound:
            continue

    if tab_key == "Склад":
        worksheet = spreadsheet.get_worksheet(0)
        if worksheet is not None:
            warnings.append(
                f"Лист «{desired}» не найден по имени. Загружен первый лист «{worksheet.title}»."
            )
            return worksheet, worksheet.title, warnings

    raise LookupError(
        f"Не удалось найти лист «{desired}». {last_error or ''} "
        f"Проверьте названия вкладок или SHEET_GIDS в .env."
    )


def _detect_header_row(values: list[list[str]], expected: list[str] | None) -> int:
    if not values or not expected:
        return 0

    expected_keys = {_normalize_cell(c).casefold() for c in expected}
    best_index = 0
    best_score = 0

    for index, row in enumerate(values[:30]):
        row_keys = {
            _normalize_cell(cell).casefold()
            for cell in row
            if _normalize_cell(cell)
        }
        score = len(expected_keys & row_keys)
        if score > best_score:
            best_score = score
            best_index = index

    threshold = max(2, (len(expected) + 1) // 2)
    if best_score >= threshold:
        return best_index
    return 0


def _rename_warehouse_headers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty and len(df.columns) == 0:
        return df

    rename: dict[str, str] = {}
    for col in df.columns:
        key = _normalize_cell(col).casefold()
        canonical = WAREHOUSE_HEADER_ALIASES.get(key)
        if canonical:
            rename[col] = canonical

    if rename:
        df = df.rename(columns=rename)

    if df.columns.duplicated().any():
        merged: dict[str, pd.Series] = {}
        for col in dict.fromkeys(df.columns):
            parts = df.loc[:, df.columns == col]
            if parts.shape[1] == 1:
                merged[col] = parts.iloc[:, 0]
            else:
                merged[col] = parts.apply(
                    lambda row: next(
                        (v for v in row if _normalize_cell(v)), ""
                    ),
                    axis=1,
                )
        df = pd.DataFrame(merged)

    return df


def _align_dataframe_columns(tab_key: str, df: pd.DataFrame) -> pd.DataFrame:
    expected = EXPECTED_COLUMNS.get(tab_key)
    if not expected:
        return df

    if tab_key == "Склад":
        df = _rename_warehouse_headers(df)

    if df.empty and len(df.columns) == 0:
        df = pd.DataFrame({col: pd.Series(dtype="string") for col in expected})
        return df

    for col in expected:
        if col not in df.columns:
            df[col] = ""
    extra = [c for c in df.columns if c not in expected]
    df = df.reindex(columns=expected + extra)
    for col in expected:
        df[col] = df[col].astype("string")
    return df


def _values_to_dataframe(values: list[list[str]]) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    if not values:
        warnings.append("Лист полностью пустой — нет даже строки заголовков.")
        return pd.DataFrame(), warnings

    raw_headers = values[0]
    headers: list[str] = []
    for index, cell in enumerate(raw_headers):
        name = _normalize_cell(cell)
        headers.append(name if name else f"Колонка_{index + 1}")

    while headers:
        idx = len(headers) - 1
        if headers[idx].startswith("Колонка_") and (
            idx >= len(raw_headers) or not _normalize_cell(raw_headers[idx])
        ):
            headers.pop()
        else:
            break

    if not headers:
        warnings.append("Первая строка листа не содержит заголовков колонок.")
        return pd.DataFrame(), warnings

    rows: list[list[str]] = []
    for row in values[1:]:
        if not any(_normalize_cell(cell) for cell in row):
            continue
        padded = row + [""] * max(0, len(headers) - len(row))
        rows.append(padded[: len(headers)])

    if not rows:
        warnings.append(
            f"Есть заголовки ({headers}), но нет строк с данными под ними."
        )
        return pd.DataFrame(columns=headers), warnings

    return pd.DataFrame(rows, columns=headers), warnings


def _column_debug(tab_key: str, df: pd.DataFrame) -> list[str]:
    expected = EXPECTED_COLUMNS.get(tab_key)
    if not expected:
        return []
    actual = [str(c) for c in df.columns]
    if actual == expected:
        return []
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    lines = [
        "Заголовки в Google Таблице не совпадают с ожидаемыми для вкладки «"
        + tab_key
        + "».",
        f"Ожидается: {expected}",
        f"В первой строке листа: {actual}",
    ]
    if missing:
        lines.append(f"Не хватает колонок: {missing}")
    if extra:
        lines.append(f"Лишние или другие колонки: {extra}")
    lines.append(
        "Проверьте строку 1 в Google Sheets (без объединённых ячеек, без дубликатов имён)."
    )
    return lines


def _fetch_sheet_values_gspread(
    tab_key: str,
) -> tuple[list[list[str]], str, list[str]]:
    from gspread.exceptions import APIError

    client = get_gspread_client()
    spreadsheet = _open_spreadsheet(client)
    worksheet, resolved_title, resolve_warnings = _resolve_worksheet(
        spreadsheet, tab_key
    )
    try:
        values = worksheet.get_all_values()
    except APIError as exc:
        raise LookupError(
            f"Google Sheets API: {exc}. {_SERVICE_ACCOUNT_HINT}"
        ) from exc
    return values, resolved_title, resolve_warnings


@st.cache_data(ttl=30, show_spinner="Загрузка данных…")
def fetch_sheet(tab_key: str) -> tuple[pd.DataFrame, dict]:
    """Загрузка листа: локальный CSV, публичный экспорт или Google Sheets API."""
    use_local = DATA_SOURCE == "local_csv"
    auth_mode = "local_csv" if use_local else _resolve_auth_mode()
    meta: dict = {
        "worksheet_title": "",
        "spreadsheet_id": SPREADSHEET_ID,
        "local_csv_path": str(_resolve_local_csv_path() or ""),
        "row_count": 0,
        "warnings": [],
        "source": auth_mode,
    }

    if not use_local and not SPREADSHEET_ID:
        meta["warnings"].append("SPREADSHEET_ID не задан в .env")
        return pd.DataFrame(), meta

    try:
        if use_local:
            values, resolved_title, resolve_warnings = _fetch_sheet_local_csv(tab_key)
        elif auth_mode == "public_csv":
            values, resolved_title, resolve_warnings = _fetch_sheet_public_csv(tab_key)
        else:
            values, resolved_title, resolve_warnings = _fetch_sheet_values_gspread(
                tab_key
            )
    except FileNotFoundError as exc:
        meta["warnings"].append(str(exc))
        return pd.DataFrame(), meta
    except LookupError as exc:
        meta["warnings"].append(str(exc))
        return pd.DataFrame(), meta
    except Exception as exc:
        meta["warnings"].append(f"Ошибка загрузки: {exc}")
        return pd.DataFrame(), meta

    meta["worksheet_title"] = resolved_title
    meta["warnings"].extend(resolve_warnings)

    if not values:
        meta["row_count"] = 0
        return pd.DataFrame(), meta

    while values and not any(_normalize_cell(cell) for cell in values[0]):
        values = values[1:]

    expected = EXPECTED_COLUMNS.get(tab_key)
    header_row = _detect_header_row(values, expected)
    if header_row > 0:
        meta["warnings"].append(
            f"Заголовки колонок найдены в строке {header_row + 1} листа "
            f"(данные читаются начиная с неё)."
        )
        values = values[header_row:]

    df, parse_warnings = _values_to_dataframe(values)
    meta["warnings"].extend(parse_warnings)

    df = _align_dataframe_columns(tab_key, df)
    meta["warnings"].extend(_column_debug(tab_key, df))
    meta["row_count"] = len(df)

    return df, meta


def load_sheet(tab_key: str) -> pd.DataFrame:
    df, _ = fetch_sheet(tab_key)
    return df


def _image_to_data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def inject_mixmann_theme() -> None:
    css = BRAND_CSS_PATH.read_text(encoding="utf-8")
    st.html(f"<style>{css}</style>")


def _esc(value: object) -> str:
    return html.escape(str(value) if value is not None else "")


def _render_html(fragment: str) -> None:
    st.html(textwrap.dedent(fragment).strip())


_METRIC_CONFIG: dict[str, dict[str, str]] = {
    "Склад": {
        "icon": "warehouse",
        "variant": "teal",
        "hint": "позиций на складе",
    },
    "Операции": {
        "icon": "shopping_cart",
        "variant": "blue",
        "hint": "записей операций",
    },
    "Расходы": {
        "icon": "account_balance_wallet",
        "variant": "amber",
        "hint": "статей расходов",
    },
}


def render_brand_header(spreadsheet_link: str) -> None:
    _render_html(
        f"""
        <header class="app-topbar">
            <div class="app-topbar__inner">
                <div class="app-topbar__left">
                    <button type="button"
                            class="app-topbar__menu"
                            data-nav-toggle
                            aria-label="Открыть меню"
                            aria-expanded="false">
                        <span class="material-symbols-rounded" aria-hidden="true">menu</span>
                    </button>
                    <h1 class="app-topbar__brand">
                        Mixmann <span class="app-topbar__brand-accent">CRM</span>
                    </h1>
                </div>
                <div class="profile-menu" data-profile-menu>
                    <button type="button"
                            class="profile-menu__trigger"
                            aria-label="Меню профиля"
                            aria-haspopup="true"
                            aria-expanded="false">
                        <span class="profile-menu__icon material-symbols-rounded"
                              aria-hidden="true">account_circle</span>
                    </button>
                    <div class="profile-menu__dropdown" role="menu" hidden>
                        <a class="profile-menu__item"
                           role="menuitem"
                           href="{_esc(spreadsheet_link)}"
                           target="_blank"
                           rel="noopener noreferrer">
                            <span class="material-symbols-rounded" aria-hidden="true">table</span>
                            Google Таблица
                        </a>
                        <button type="button"
                                class="profile-menu__item profile-menu__item--deploy"
                                role="menuitem"
                                data-deploy-trigger>
                            <span class="material-symbols-rounded" aria-hidden="true">rocket_launch</span>
                            Deploy
                        </button>
                    </div>
                </div>
            </div>
        </header>
        <script>
        (() => {{
            const menu = document.querySelector("[data-profile-menu]");
            if (!menu || menu.dataset.bound) return;
            menu.dataset.bound = "1";

            const trigger = menu.querySelector(".profile-menu__trigger");
            const dropdown = menu.querySelector(".profile-menu__dropdown");
            const deployBtn = menu.querySelector("[data-deploy-trigger]");

            const closeMenu = () => {{
                dropdown.hidden = true;
                trigger.setAttribute("aria-expanded", "false");
            }};

            trigger.addEventListener("click", (event) => {{
                event.stopPropagation();
                const open = dropdown.hidden;
                dropdown.hidden = !open;
                trigger.setAttribute("aria-expanded", open ? "true" : "false");
            }});

            document.addEventListener("click", (event) => {{
                if (!menu.contains(event.target)) closeMenu();
            }});

            document.addEventListener("keydown", (event) => {{
                if (event.key === "Escape") closeMenu();
            }});

            deployBtn.addEventListener("click", () => {{
                closeMenu();
                document.querySelector('[data-testid="stDeployButton"]')?.click();
            }});

            if (!document.querySelector('[data-testid="stDeployButton"]')) {{
                deployBtn.hidden = true;
            }}

            const navToggle = document.querySelector("[data-nav-toggle]");
            const appRoot = document.querySelector(".stApp");
            let navBackdrop = document.querySelector(".app-nav-backdrop");

            if (!navBackdrop) {{
                navBackdrop = document.createElement("div");
                navBackdrop.className = "app-nav-backdrop";
                navBackdrop.hidden = true;
                document.body.appendChild(navBackdrop);
            }}

            const closeNav = () => {{
                appRoot?.classList.remove("app-nav-open");
                navToggle?.setAttribute("aria-expanded", "false");
                navBackdrop.hidden = true;
            }};

            const openNav = () => {{
                appRoot?.classList.add("app-nav-open");
                navToggle?.setAttribute("aria-expanded", "true");
                navBackdrop.hidden = false;
            }};

            navToggle?.addEventListener("click", (event) => {{
                event.stopPropagation();
                if (appRoot?.classList.contains("app-nav-open")) {{
                    closeNav();
                }} else {{
                    openNav();
                }}
            }});

            navBackdrop.addEventListener("click", closeNav);

            document.addEventListener("keydown", (event) => {{
                if (event.key === "Escape" && appRoot?.classList.contains("app-nav-open")) {{
                    closeNav();
                }}
            }});
        }})();
        </script>
        """
    )


def render_key_metrics() -> None:
    cols = st.columns(len(TABS))
    for col, tab_key in zip(cols, TABS):
        cfg = _METRIC_CONFIG[tab_key]
        try:
            df, meta = fetch_sheet(tab_key)
            count = meta.get("row_count", len(df))
            value = str(count)
        except Exception:
            value = "—"

        col.metric(
            label=tab_key,
            value=value,
            help=cfg["hint"],
            border=True,
        )

    style_metric_cards(
        background_color="rgba(255, 255, 255, 0.82)",
        border_left_color="#0d9488",
        border_color="rgba(15, 23, 42, 0.06)",
        border_radius_px=16,
        box_shadow=True,
    )


def _resolve_active_nav() -> str:
    nav = st.query_params.get("nav", "Склад")
    return nav if nav in NAV_ITEMS else "Склад"


def render_side_navigation() -> str:
    nav_options = list(NAV_ITEMS.keys())
    active = _resolve_active_nav()
    manual_select = nav_options.index(active) if active in nav_options else 0

    with st.sidebar:
        selected = option_menu(
            "Разделы",
            nav_options,
            icons=[NAV_ITEMS[label]["icon"] for label in nav_options],
            menu_icon="list",
            default_index=manual_select,
            manual_select=manual_select,
            styles=OPTION_MENU_STYLES,
            key="main_nav",
        )
        render_sidebar_branding()

    if selected != active:
        st.query_params["nav"] = selected
        if "product" in st.query_params:
            del st.query_params["product"]
        st.rerun()

    return selected


def render_sidebar_branding() -> None:
    _render_html(
        """
        <div class="glass-sidebar-footer">
            <span class="glass-sidebar-footer__brand">Mixmann</span>
            <span class="glass-sidebar-footer__tagline"> — строительные смеси</span>
            <div class="glass-sidebar-dots" aria-hidden="true">
                <span class="dot-teal"></span>
                <span class="dot-blue"></span>
                <span class="dot-sand"></span>
            </div>
        </div>
        """
    )


def render_settings(spreadsheet_link: str) -> None:
    st.subheader("Настройки")
    st.caption("Подключение к данным и параметры приложения")

    st.markdown("#### Подключение")
    if DATA_SOURCE == "local_csv":
        local_path = _resolve_local_csv_path()
        if local_path:
            st.success(f"Локальный CSV · {local_path.name}")
            st.caption(f"Путь: `{local_path}`")
        else:
            st.error(
                "Файл не найден. Положите «МойСклад - Склад.csv» в папку проекта "
                "или задайте LOCAL_CSV_FILE в .env."
            )
    else:
        mode = _resolve_auth_mode()
        labels = {
            "public_csv": "Публичный CSV-экспорт",
            "service_account": "Google Sheets API · сервисный аккаунт",
            "oauth": "Google Sheets API · OAuth",
        }
        detail = labels.get(mode, mode)
        if mode == "service_account":
            detail += f" · {CREDENTIALS_FILE.name}"
        elif mode == "oauth":
            detail += f" · {TOKEN_FILE.name}"
        st.success(labels.get(mode, mode))
        st.caption(detail)
        st.caption(f"ID таблицы: `{SPREADSHEET_ID}`")
        if SHEET_GIDS:
            st.caption("Gid листов заданы через SHEET_GIDS в .env")

    st.markdown("#### Google Таблица")
    st.link_button(
        "Открыть таблицу",
        spreadsheet_link,
        use_container_width=False,
    )


def _render_empty_state(title: str, text: str) -> None:
    st.info(f"📭 **{title}**\n\n{text}")


def _filter_warehouse_rows(
    df: pd.DataFrame, search: str
) -> list[tuple[int, dict[str, Any]]]:
    query = search.strip().casefold()
    filtered: list[tuple[int, dict[str, Any]]] = []
    for idx, series in df.iterrows():
        row = series.to_dict()
        if query:
            haystack = " ".join(_normalize_cell(row.get(col, "")) for col in df.columns)
            if query not in haystack.casefold():
                continue
        filtered.append((int(idx), row))
    return filtered


def _resolve_selected_product_idx(row_count: int) -> int | None:
    raw = st.query_params.get("product", "")
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        return None
    if idx < 0 or idx >= row_count:
        return None
    return idx


def _warehouse_header_map(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for col_idx, header in enumerate(headers):
        key = _normalize_cell(header).casefold()
        canonical = WAREHOUSE_HEADER_ALIASES.get(key, _normalize_cell(header))
        if canonical not in mapping:
            mapping[canonical] = col_idx
    return mapping


def _save_warehouse_row_local(row_idx: int, row_data: dict[str, str]) -> None:
    path = _resolve_local_csv_path()
    if path is None:
        raise FileNotFoundError(
            "Файл склада не найден. Задайте LOCAL_CSV_FILE в .env."
        )

    expected = EXPECTED_COLUMNS["Склад"]
    csv_text = _read_text_file(path)
    values = _csv_text_to_values(csv_text)
    if not values:
        raise LookupError("CSV-файл пустой.")

    header_row_idx = _detect_header_row(values, expected)
    headers = values[header_row_idx]
    header_map = _warehouse_header_map(headers)
    data_row_idx = header_row_idx + 1 + row_idx
    if data_row_idx >= len(values):
        raise IndexError("Строка товара не найдена в файле.")

    row = list(values[data_row_idx])
    max_cols = max(len(headers), len(row), max(header_map.values(), default=-1) + 1)
    if len(row) < max_cols:
        row.extend([""] * (max_cols - len(row)))

    for col in expected:
        if col not in row_data or col not in header_map:
            continue
        row[header_map[col]] = _normalize_cell(row_data[col])

    values[data_row_idx] = row

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(values)
    path.write_text(buffer.getvalue(), encoding="utf-8-sig")


def _close_product_drawer() -> None:
    if "product" in st.query_params:
        del st.query_params["product"]


def _render_product_drawer(
    df: pd.DataFrame, row_idx: int, meta: dict[str, Any]
) -> None:
    if row_idx < 0 or row_idx >= len(df):
        _close_product_drawer()
        return

    row = df.iloc[row_idx]
    columns = [col for col in EXPECTED_COLUMNS["Склад"] if col in df.columns]
    can_save = meta.get("source") == "local_csv"
    product_name = _normalize_cell(row.get("Наименование", "")) or "Товар"
    category = _normalize_cell(row.get("Категория", ""))
    nav_q = quote("Склад")
    close_href = f"?nav={nav_q}"

    _render_html(
        f"""
        <a class="product-drawer-backdrop"
           href="{close_href}"
           aria-label="Закрыть панель"></a>
        """
    )

    st.markdown(
        '<div class="product-drawer-active" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

    header_left, header_right = st.columns([6, 1], gap="small")
    with header_left:
        st.markdown(
            f'<p class="product-drawer-eyebrow">{_esc(category) or "Без категории"}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(f"### {_esc(product_name)}")
    with header_right:
        st.link_button("✕", close_href, help="Закрыть")

    st.caption("Детали позиции на складе")

    with st.form("product_edit_form", clear_on_submit=False):
        updated: dict[str, str] = {}
        for col in columns:
            updated[col] = st.text_input(
                col,
                value=_normalize_cell(row.get(col, "")),
                disabled=not can_save,
            )

        actions = st.columns(2, gap="small")
        with actions[0]:
            cancel = st.form_submit_button("Отмена", use_container_width=True)
        with actions[1]:
            save = st.form_submit_button(
                "Сохранить",
                type="primary",
                use_container_width=True,
                disabled=not can_save,
            )

    if cancel:
        _close_product_drawer()
        st.rerun()

    if save and can_save:
        name = _normalize_cell(updated.get("Наименование", ""))
        if not name:
            st.error("Укажите наименование товара.")
        else:
            try:
                _save_warehouse_row_local(row_idx, updated)
                fetch_sheet.clear()
                _close_product_drawer()
                st.rerun()
            except Exception as exc:
                st.error(f"Не удалось сохранить: {exc}")

    if not can_save:
        st.info(
            "Сохранение из приложения доступно только для локального CSV. "
            "Для Google Таблицы откройте её через меню профиля."
        )


def _render_warehouse_table(
    df: pd.DataFrame, search: str = "", selected_idx: int | None = None
) -> None:
    if df.empty:
        return

    rows = _filter_warehouse_rows(df, search)
    if not rows:
        _render_empty_state(
            "Ничего не найдено",
            "Попробуйте изменить запрос поиска или сбросить фильтр.",
        )
        return

    columns = [col for col in EXPECTED_COLUMNS["Склад"] if col in df.columns]
    if not columns:
        columns = list(df.columns)

    rows.sort(
        key=lambda item: (
            _normalize_cell(item[1].get("Категория", "")).casefold(),
            _normalize_cell(item[1].get("Наименование", "")).casefold(),
        )
    )

    nav_q = quote("Склад")
    header_cells = "".join(f"<th scope=\"col\">{_esc(col)}</th>" for col in columns)
    body_rows: list[str] = []
    for row_idx, row in rows:
        selected_class = (
            " warehouse-table__row--selected"
            if selected_idx is not None and row_idx == selected_idx
            else ""
        )
        cells = "".join(
            (
                f"<td data-label=\"{_esc(col)}\">"
                f"{_esc(_normalize_cell(row.get(col, '')) or '—')}</td>"
            )
            for col in columns
        )
        body_rows.append(
            f"""
            <tr class="warehouse-table__row--clickable{selected_class}"
                data-product-idx="{row_idx}"
                data-product-href="?nav={nav_q}&amp;product={row_idx}"
                tabindex="0"
                role="button"
                aria-label="Открыть карточку товара">
                {cells}
            </tr>
            """
        )

    _render_html(
        f"""
        <div class="warehouse-table-panel">
            <div class="warehouse-table-wrap">
                <table class="warehouse-table">
                    <thead>
                        <tr>{header_cells}</tr>
                    </thead>
                    <tbody>
                        {"".join(body_rows)}
                    </tbody>
                </table>
            </div>
        </div>
        <script>
        (() => {{
            const rows = document.querySelectorAll("[data-product-href]");
            if (!rows.length || rows[0].dataset.bound) return;
            rows[0].dataset.bound = "1";

            const openProduct = (href) => {{
                if (!href) return;
                window.location.href = href;
            }};

            rows.forEach((row) => {{
                row.addEventListener("click", () => openProduct(row.dataset.productHref));
                row.addEventListener("keydown", (event) => {{
                    if (event.key === "Enter" || event.key === " ") {{
                        event.preventDefault();
                        openProduct(row.dataset.productHref);
                    }}
                }});
            }});

            document.addEventListener("keydown", (event) => {{
                if (event.key !== "Escape") return;
                if (!document.querySelector(".product-drawer-active")) return;
                const backdrop = document.querySelector(".product-drawer-backdrop");
                if (backdrop?.href) window.location.href = backdrop.href;
            }});
        }})();
        </script>
        """
    )


def _render_refresh_fab(tab_key: str) -> None:
    refresh_key = f"refresh_{tab_key}"
    st.markdown(
        f'<div class="refresh-trigger-hidden" data-refresh-marker="{_esc(tab_key)}"></div>',
        unsafe_allow_html=True,
    )
    if st.button("↻", key=refresh_key, help="Обновить данные"):
        fetch_sheet.clear()
        st.rerun()

    _render_html(
        f"""
        <button type="button"
                class="fab-refresh"
                data-refresh-fab="{_esc(tab_key)}"
                aria-label="Обновить данные">
            <span class="material-symbols-rounded" aria-hidden="true">refresh</span>
        </button>
        <script>
        (() => {{
            const fab = document.querySelector('[data-refresh-fab="{_esc(tab_key)}"]');
            if (!fab || fab.dataset.bound) return;
            fab.dataset.bound = "1";

            fab.addEventListener("click", () => {{
                const marker = document.querySelector(
                    '[data-refresh-marker="{_esc(tab_key)}"]'
                );
                const btnHost = marker?.closest('[data-testid="stElementContainer"]')
                    ?.nextElementSibling;
                btnHost?.querySelector("button")?.click();
            }});
        }})();
        </script>
        """
    )


def render_tab(tab_key: str) -> None:
    try:
        df, meta = fetch_sheet(tab_key)
    except Exception as exc:
        st.error(f"Не удалось загрузить лист: {exc}")
        return

    for message in meta.get("warnings", []):
        st.warning(message)

    sheet_label = meta.get("worksheet_title") or TABS[tab_key]
    sheet_row_count = meta.get("row_count", len(df))
    auth_label = meta.get("source", "public_csv")

    search = ""
    if tab_key == "Склад" and not df.empty:
        search = st.text_input(
            "Поиск по складу",
            placeholder="Наименование, категория, примечание…",
            key=f"search_{tab_key}",
            label_visibility="collapsed",
        )

    st.subheader(tab_key)
    st.caption(
        f"{sheet_label} · {sheet_row_count} записей · {auth_label}"
    )

    if df.empty:
        if meta.get("source") == "local_csv" and tab_key != "Склад":
            _render_empty_state(
                "Данные недоступны",
                "Для этой вкладки локальный файл не используется — "
                "в папке проекта только CSV склада.",
            )
        elif meta.get("source") == "local_csv":
            _render_empty_state(
                "Склад пуст",
                "Проверьте файл CSV в папке проекта или LOCAL_CSV_FILE в .env.",
            )
        else:
            _render_empty_state(
                "Нет данных",
                "Проверьте доступ к таблице, названия листов (SHEET_GIDS) "
                "или добавьте строки в Google Sheets.",
            )
        _render_refresh_fab(tab_key)
        return

    if tab_key == "Склад":
        selected_idx = _resolve_selected_product_idx(len(df))
        _render_warehouse_table(df, search, selected_idx)
        if selected_idx is not None:
            _render_product_drawer(df, selected_idx, meta)
    else:
        filtered_df = dataframe_explorer(df, case=False)
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            key=f"table_{tab_key}",
        )

    _render_refresh_fab(tab_key)

    if meta.get("source") == "local_csv":
        csv_name = meta.get("worksheet_title") or "CSV"
        st.caption(
            f"Данные из файла «{csv_name}» в папке проекта. "
            "Нажмите на строку, чтобы открыть карточку товара и отредактировать её."
        )
    else:
        st.caption(
            "Редактирование — в Google Таблице (меню профиля в правом верхнем углу). "
            "Приложение читает данные через публичный экспорт CSV или API."
        )


def main() -> None:
    page_icon = str(FAVICON_PATH) if FAVICON_PATH.exists() else "📦"
    st.set_page_config(
        page_title="Mixmann CRM",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_mixmann_theme()

    sheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    render_brand_header(sheet_url)

    active_nav = render_side_navigation()

    if active_nav != "Настройки":
        render_key_metrics()

    if active_nav == "Настройки":
        render_settings(sheet_url)
    elif active_nav in TABS:
        render_tab(active_nav)


if __name__ == "__main__":
    main()
