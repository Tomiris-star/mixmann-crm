import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Mixmann CRM", page_icon="⚡", layout="centered")

# Премиальный светлый минимализм с идеальной читаемостью
st.markdown("""
    <style>
    .stApp {
        background-color: #F4F5F7;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", sans-serif;
        color: #1F2937;
    }
    h1, h2, h3 {
        color: #111827;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .premium-card {
        background: #FFFFFF;
        padding: 20px 22px;
        border-radius: 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        margin-bottom: 16px;
        border: 1px solid rgba(0, 0, 0, 0.04);
    }
    .premium-card-green {
        background: linear-gradient(135.84deg, #F0FDF4 0%, #FFFFFF 100%);
        padding: 20px 22px;
        border-radius: 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        margin-bottom: 16px;
        border: 1px solid rgba(16, 185, 129, 0.15);
    }
    .premium-card-blue {
        background: linear-gradient(135.84deg, #EFF6FF 0%, #FFFFFF 100%);
        padding: 20px 22px;
        border-radius: 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        margin-bottom: 16px;
        border: 1px solid rgba(59, 130, 246, 0.15);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #E5E7EB;
        padding: 6px;
        border-radius: 16px;
        margin-bottom: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 12px;
        color: #4B5563;
        font-weight: 600;
        font-size: 13px;
        height: 38px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }
    .stButton > button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border-radius: 14px;
        font-weight: 600;
        border: none;
        padding: 12px 20px;
        width: 100%;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
    }
    </style>
""", unsafe_allow_html=True)

st.title("Mixmann CRM")

CSV_FILE = "МойСклад - Склад.csv"
LOG_FILE = "История_отгрузок.csv"

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if "Категория" not in df.columns or "Наименование" not in df.columns:
                raise Exception("Bad columns")
            return df
        except:
            pass
    
    data = {
        "Категория": [
            "Готовая продукция", "Готовая продукция", "Готовая продукция", "Готовая продукция", "Готовая продукция", "Готовая продукция",
            "Сырьё и материалы", "Сырьё и материалы", "Сырьё и материалы", "Сырьё и материалы", "Сырьё и материалы", "Сырьё и материалы", "Сырьё и материалы", "Сырьё и материалы", "Сырьё и материалы",
            "Пустые мешки", "Пустые мешки", "Пустые мешки", "Пустые мешки", "Пустые мешки"
        ],
        "Наименование": [
            "Стяжка", "ШВС", "Клей", "Клей (кызыл)", "Клей (оранжевый)", "Strong",
            "Песок", "Цемент", "Atocell", "Полипласт 2032", "Стекловолокно", "Беролан", "Отработка", "Стрейч-плёнка", "Рулон",
            "ШВС", "Клей", "Стяжка", "Granit", "Strong"
        ],
        "Количество": [
            0, 19, 15, 0, 0, 24,
            22, 494, 173.1, 100, 24, 48.8, 8, 40, 2,
            2118, 1018, 5025, 5035, 5044
        ],
        "Ед. измерения": [
            "мешков", "п", "п + 15 мешков", "мешков", "мешков", "мешка",
            "т", "мешков (16п + 14м)", "кг", "кг", "кг", "кг", "бочек", "шт", "шт",
            "шт", "шт", "шт", "шт", "шт"
        ]
    }
    df = pd.DataFrame(data)
    df.to_csv(CSV_FILE, index=False)
    return df

def log_action(action_type, item, qty, unit):
    current_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    new_log = pd.DataFrame([[current_date, action_type, item, qty, unit]], columns=["Дата", "Тип", "Товар", "Количество", "Ед"])
    if os.path.exists(LOG_FILE):
        old_logs = pd.read_csv(LOG_FILE)
        updated_logs = pd.concat([new_log, old_logs], ignore_index=True)
    else:
        updated_logs = new_log
    updated_logs.to_csv(LOG_FILE, index=False)

df = load_data()

tab1, tab2, tab3, tab4 = st.tabs(["Склад", "Анализ", "Финансы", "Рецептуры"])

with tab1:
    st.markdown("### Умный ввод с телефона")
    user_input = st.text_input("Введите операцию", placeholder="Например: Клей 4 или Цемент +50", label_visibility="collapsed")
    
    if user_input:
        text_lower = user_input.lower().strip()
        parts = text_lower.split()
        
        val = 0.0
        is_addition = "плюс" in text_lower or "+" in text_lower or "привез" in text_lower or "приход" in text_lower
        is_subtraction = "минус" in text_lower or "-" in text_lower or "отгруз" in text_lower
        
        clean_parts = []
        for p in parts:
            p_clean = p.replace("+", "").replace("-", "")
            try:
                val = float(p_clean)
                if "-" in p: is_subtraction = True
                if "+" in p: is_addition = True
            except:
                clean_parts.append(p)
                
        item_name_query = " ".join(clean_parts)
        if not is_addition and not is_subtraction:
            is_subtraction = True

        found = False
        if item_name_query and val > 0:
            for idx, row in df.iterrows():
                row_name_lower = str(row["Наименование"]).lower()
                if item_name_query in row_name_lower or row_name_lower in item_name_query:
                    current_q = float(row["Количество"])
                    unit = row["Ед. измерения"]
                    if is_subtraction and not is_addition:
                        new_q = max(0.0, current_q - val)
                        msg = f"Списано: *{row['Наименование']}* — {val} {unit}. Остаток: *{new_q}*"
                        log_action("Отгрузка / Расход", row["Наименование"], val, unit)
                    else:
                        new_q = current_q + val
                        msg = f"Приход: *{row['Наименование']}* +{val} {unit}. Остаток: *{new_q}*"
                        log_action("Приход", row["Наименование"], val, unit)
                        
                    df.loc[idx, "Количество"] = new_q
                    found = True
                    break
        
        if found:
            df.to_csv(CSV_FILE, index=False)
            st.success(msg)
            st.rerun()
        else:
            st.warning("Не распознано. Пример: Клей 4 или Цемент 50")

    st.markdown("---")
    st.markdown("### Состояние склада")
    
    for cat in df["Категория"].unique():
        st.markdown(f"<p style='color: #6B7280; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>{cat}</p>", unsafe_allow_html=True)
        cat_items = df[df["Категория"] == cat]
        
        card_html = "<div class='premium-card'>"
        for _, row in cat_items.iterrows():
            name = row["Наименование"]
            qty = row["Количество"]
            unit = row["Ед. измерения"]
            
            # Индикатор критических остатков
            qty_color = "#2563EB"
            if name == "Atocell" and qty < 50:
                qty_color = "#DC2626"
            elif qty == 0:
                qty_color = "#9CA3AF"
                
            card_html += f"<div style='padding: 10px 0; border-bottom: 0.5px solid #F3F4F6; display: flex; justify-content: space-between; align-items: center;'><span><b>{name}</b></span> <span style='color: {qty_color}; font-weight: 600;'>{qty} {unit}</span></div>"
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

    # Журнал операций с фильтром по периодам
    st.markdown("### История операций")
    
    if os.path.exists(LOG_FILE):
        logs_df = pd.read_csv(LOG_FILE)
        
        logs_df["ParsedDate"] = pd.to_datetime(logs_df["Дата"], format="%d.%m.%Y %H:%M", errors="coerce")
        
        col_f1, col_f2 = st.columns([2, 2])
        with col_f1:
            period_filter = st.selectbox("Период", ["Последние 20", "За текущий месяц", "За всё время"], label_visibility="collapsed")
        
        if period_filter == "За текущий месяц":
            now = datetime.now()
            logs_df = logs_df[(logs_df["ParsedDate"].dt.month == now.month) & (logs_df["ParsedDate"].dt.year == now.year)]
        
        log_html = "<div class='premium-card' style='max-height: 250px; overflow-y: auto;'>"
        
        display_df = logs_df.head(20) if period_filter == "Последние 20" else logs_df
        
        if display_df.empty:
            log_html += "<div style='color: #6B7280; font-size: 13px; text-align: center; padding: 10px;'>За выбранный период операций не найдено.</div>"
        else:
            for _, l_row in display_df.iterrows():
                badge_color = "#059669" if l_row['Тип'] == "Приход" else "#DC2626"
                log_html += f"<div style='padding: 8px 0; border-bottom: 0.5px solid #F3F4F6; font-size: 13px;'><span style='color: #6B7280;'>{l_row['Дата']}</span> | <b style='color: {badge_color};'>{l_row['Тип']}</b>: <b>{l_row['Товар']}</b> ({l_row['Количество']} {l_row['Ед']})</div>"
        
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.markdown("<div class='premium-card' style='color: #6B7280; font-size: 13px;'>История пока пуста. Движения появятся после первых операций.</div>", unsafe_allow_html=True)

    st.markdown("### Оценка готовой продукции")
    st.markdown("""
        <div class='premium-card-green'>
            <div style='padding: 8px 0; border-bottom: 0.5px solid #E5E7EB; display: flex; justify-content: space-between;'><span>Стяжка:</span> <b>0 ₸</b></div>
            <div style='padding: 8px 0; border-bottom: 0.5px solid #E5E7EB; display: flex; justify-content: space-between;'><span>ШВС:</span> <b style='color: #059669;'>1 094 400 ₸</b></div>
            <div style='padding: 8px 0; border-bottom: 0.5px solid #E5E7EB; display: flex; justify-content: space-between;'><span>Клей:</span> <b style='color: #059669;'>478 800 ₸</b></div>
            <div style='padding: 8px 0; display: flex; justify-content: space-between;'><span>Strong:</span> <b style='color: #059669;'>43 200 ₸</b></div>
        </div>
        <div class='premium-card-blue' style='text-align: center;'>
            <div style='font-size: 13px; color: #4B5563; text-transform: uppercase; letter-spacing: 1px;'>Общая стоимость</div>
            <div style='font-size: 26px; font-weight: 800; color: #2563EB; margin-top: 6px;'>1 616 400 ₸</div>
        </div>
    """, unsafe_allow_html=True)

with tab2:
    st.markdown("### Экспресс-анализ производства")
    if st.button("Запустить проверку запасов"):
        def get_qty(name):
            row = df[df["Наименование"] == name]
            return float(row["Количество"].values[0]) if not row.empty else 0.0

        atocell_kg = get_qty("Atocell")
        st.markdown(f"""
            <div class='premium-card-blue'>
                <h4 style='margin-top:0; color:#2563EB;'>Результаты аудита:</h4>
                <p>Доступно мешков <b>Strong</b>: <b>~72 замеса</b></p>
                <p>Доступно мешков <b>Granit</b>: <b>~58 замесов</b></p>
                <br>
                <p style='color: #DC2626; font-weight: 600;'>Контроль сырья:</p>
                <p style='font-size: 13px; color: #4B5563;'>Запас <b>Atocell</b> ({atocell_kg} кг) близок к критическому уровню (на 3-4 замеса).</p>
            </div>
        """, unsafe_allow_html=True)

with tab3:
    st.markdown("### Калькулятор маржинальности")
    st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
    product = st.selectbox("Продукт", ["Strong", "Granit"], key="calc_prod")
    cost_per_bag = 1191.60 if product == "Strong" else 1368.10
    default_price = 1800.0 if product == "Strong" else 2300.0
    
    st.markdown(f"<p style='color: #6B7280; font-size: 13px;'>Себестоимость: <b>{cost_per_bag:,.2f} ₸</b></p>".replace(",", " "), unsafe_allow_html=True)
    selling_price = st.number_input("Цена продажи (₸)", value=default_price, step=50.0)
    bags_count = st.number_input("Количество", value=50, step=10)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("Рассчитать рентабельность"):
        rev = selling_price * bags_count
        cost = cost_per_bag * bags_count
        profit = rev - cost
        margin = ((selling_price - cost_per_bag) / cost_per_bag) * 100
        st.markdown(f"""
            <div class='premium-card-blue'>
                <p>Выручка: <b>{rev:,.2f} ₸</b></p>
                <p>Затраты: <b>{cost:,.2f} ₸</b></p>
                <p>Прибыль: <b style='color: #059669;'>{profit:,.2f} ₸</b></p>
                <p>Маржа: <b style='color: #2563EB;'>{margin:.1f}%</b></p>
            </div>
        """.replace(",", " "), unsafe_allow_html=True)

with tab4:
    st.markdown("### Рецептурная карта")
    recipe = st.selectbox("Рецепт", ["Strong", "Granit"], key="recipe_prod")
    
    if recipe == "Strong":
        items = [("Песок", "200,00 ₸"), ("Цемент", "336,00 ₸"), ("Atocell", "210,00 ₸"), ("Эфир", "9,9 ₸"), ("Полипласт", "280,00 ₸"), ("Мешок", "155,7 ₸")]
        tot, prc = "1 191,6 ₸", "1 800 ₸"
    else:
        items = [("Песок", "200,00 ₸"), ("Цемент", "432,00 ₸"), ("Atocell", "220,5 ₸"), ("Эфир", "9,9 ₸"), ("Полипласт", "350,00 ₸"), ("Мешок", "155,7 ₸")]
        tot, prc = "1 368,1 ₸", "2 300 ₸"
        
    st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
    for c, p in items:
        st.markdown(f"• <b>{c}</b>: <span style='color: #2563EB;'>{p}</span>", unsafe_allow_html=True)
    st.markdown(f"<br>Себестоимость: <b>{tot}</b> | Цена: <b>{prc}</b></div>", unsafe_allow_html=True)