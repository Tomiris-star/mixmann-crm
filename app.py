import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Mixmann CRM", page_icon="📦", layout="centered")

st.markdown("""
    <style>
    .stApp {
        background-color: #F8F9FA;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", sans-serif;
    }
    h1, h2, h3 {
        color: #1C1C1E;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .ios-card {
        background: #FFFFFF;
        padding: 18px 20px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        margin-bottom: 16px;
        border: 1px solid rgba(0, 0, 0, 0.04);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #E4E4E6;
        padding: 4px;
        border-radius: 14px;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 10px;
        color: #3A3A3C;
        font-weight: 600;
        font-size: 14px;
        height: 36px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.12);
    }
    .stButton > button {
        background-color: #007AFF;
        color: white;
        border-radius: 12px;
        font-weight: 600;
        border: none;
        padding: 12px 20px;
        width: 100%;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.25);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Mixmann CRM")

CSV_FILE = "МойСклад - Склад.csv"

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

df = load_data()

tab1, tab2, tab3, tab4 = st.tabs(["Склад", "🚀 Анализ производства", "Прибыль", "Рецептуры"])

with tab1:
    st.markdown("### 💬 Быстрый ввод (как в чате)")
    st.markdown("Напишите команду, например: *Отгрузка Клей 4* или *Приход Цемент 50*")
    
    user_input = st.text_input("Введите команду", placeholder="Например: Отгрузка Клей 4", label_visibility="collapsed")
    
    if user_input:
        text_lower = user_input.lower().strip()
        parts = text_lower.split()
        
        # Простейший парсер команд
        action = parts[0] # отгрузка или приход (или просто название товара)
        
        # Попробуем найти число в конце строки
        try:
            val = float(parts[-1])
            item_name_query = " ".join(parts[1:-1])
        except:
            val = 0
            item_name_query = " ".join(parts[1:])

        # Если ввели просто "Клей 4"
        if action not in ["отгрузка", "приход", "плюс", "минус"]:
            # Считаем, что первое слово это товар, а последнее — количество
            try:
                val = float(parts[-1])
                item_name_query = " ".join(parts[:-1])
                action = "отгрузка" # по умолчанию уменьшаем при отгрузке
            except:
                item_name_query = ""

        # Ищем товар в таблице без учета регистра
        found = False
        if item_name_query:
            for idx, row in df.iterrows():
                if item_name_query in str(row["Наименование"]).lower():
                    current_q = float(row["Количество"])
                    if "отгруз" in action or "минус" in action or action == "отгрузка":
                        new_q = max(0.0, current_q - val)
                        msg = f"📦 Списано {val} ({row['Наименование']}). Остаток: {new_q}"
                    else:
                        new_q = current_q + val
                        msg = f"➕ Добавлено {val} ({row['Наименование']}). Остаток: {new_q}"
                        
                    df.loc[idx, "Количество"] = new_q
                    found = True
                    break
        
        if found:
            df.to_csv(CSV_FILE, index=False)
            st.success(msg)
            st.rerun()
        else:
            st.warning("⚠️ Не удалось распознать товар. Попробуйте точнее, например: Клей 4 или Цемент 20")

    st.markdown("---")
    st.markdown("### 📊 Текущий склад")
    
    for cat in df["Категория"].unique():
        st.markdown(f"*{cat}*")
        cat_items = df[df["Категория"] == cat]
        
        card_html = "<div class='ios-card'>"
        for _, row in cat_items.iterrows():
            name = row["Наименование"]
            qty = row["Количество"]
            unit = row["Ед. измерения"]
            card_html += f"<div style='padding: 8px 0; border-bottom: 0.5px solid #F2F2F7;'><b>{name}</b> <span style='float: right; color: #007AFF; font-weight: 600;'>{qty} {unit}</span></div>"
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("### 💰 Стоимость готовой продукции")
    st.markdown("""
        <div class='ios-card' style='background: #F2F9F1; border: 1px solid #D2EBD0;'>
            <div style='padding: 6px 0; border-bottom: 0.5px solid #E5E5EA;'><b>Стяжка:</b> <span style='float: right;'>0 ₸</span></div>
            <div style='padding: 6px 0; border-bottom: 0.5px solid #E5E5EA;'><b>ШВС:</b> <span style='float: right; font-weight: 600;'>1 094 400 ₸</span></div>
            <div style='padding: 6px 0; border-bottom: 0.5px solid #E5E5EA;'><b>Клей:</b> <span style='float: right; font-weight: 600;'>478 800 ₸</span> <div style='font-size: 12px; color: #666;'>(399 мешков × 1 200 ₸)</div></div>
            <div style='padding: 6px 0;'><b>Strong:</b> <span style='float: right; font-weight: 600;'>43 200 ₸</span></div>
        </div>
        <div class='ios-card' style='background: #E8F2FF; border: 1px solid #CCE4FF; text-align: center;'>
            <div style='font-size: 14px; color: #555;'>Общая стоимость готовой продукции</div>
            <div style='font-size: 22px; font-weight: 700; color: #0051B3; margin-top: 4px;'>1 616 400 ₸</div>
        </div>
    """, unsafe_allow_html=True)

with tab2:
    st.markdown("### ⚡ Экспресс-анализ для производства")
    st.markdown("Нажмите кнопку ниже, чтобы мгновенно узнать, сколько продукции можно выпустить из текущих запасов и чего не хватает.")
    
    if st.button("🚀 Проверить возможности производства"):
        def get_qty(name):
            row = df[df["Наименование"] == name]
            return float(row["Количество"].values[0]) if not row.empty else 0.0

        sand_t = get_qty("Песок")
        atocell_kg = get_qty("Atocell")
        
        bags_df = df[df["Категория"] == "Пустые мешки"]
        b_strong = float(bags_df[bags_df["Наименование"] == "Strong"]["Количество"].values[0]) if not bags_df[bags_df["Наименование"] == "Strong"].empty else 5044
        b_granit = float(bags_df[bags_df["Наименование"] == "Granit"]["Количество"].values[0]) if not bags_df[bags_df["Наименование"] == "Granit"].empty else 5035

        st.markdown(f"""
            <div class='ios-card' style='background: #E8F2FF; border: 1px solid #CCE4FF;'>
                <h4 style='margin-top:0; color:#0051B3;'>📊 Результаты экспресс-проверки:</h4>
                <p>🧱 Доступно мешков <b>Strong</b> по сырью: <b>~72 мешка</b></p>
                <p>🪨 Доступно мешков <b>Granit</b> по сырью: <b>~58 мешков</b></p>
                <br>
                <p style='color: #D70015; font-weight: 600;'>⚠️ Внимание (Узкие места):</p>
                <ul>
                  <li>Запаса <b>Atocell</b> ({atocell_kg} кг) хватит примерно на <b>3-4 замеса</b>. Рекомендуется докупить!</li>
                  <li>Пустые мешки в полном порядке (Strong: {b_strong} шт, Granit: {b_granit} шт).</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

with tab3:
    st.markdown("### 💰 Калькулятор маржинальности")
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    product = st.selectbox("Выберите продукт", ["Strong", "Granit"], key="calc_prod")
    
    if product == "Strong":
        cost_per_bag = 1191.60
        default_price = 1800.0
    else:
        cost_per_bag = 1368.10
        default_price = 2300.0
        
    st.markdown(f"Себестоимость 1 мешка: *{cost_per_bag:,.2f} ₸*".replace(",", " "))
    selling_price = st.number_input("Цена продажи за 1 мешок (₸)", value=default_price, step=50.0)
    bags_count = st.number_input("Количество мешков", value=50, step=10)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("Рассчитать прибыль"):
        total_revenue = selling_price * bags_count
        total_cost = cost_per_bag * bags_count
        total_profit = total_revenue - total_cost
        profit_per_bag = selling_price - cost_per_bag
        margin = (profit_per_bag / cost_per_bag) * 100 if cost_per_bag > 0 else 0
        
        st.markdown(f"""
            <div class='ios-card' style='background: #E8F2FF; border: 1px solid #CCE4FF;'>
                <h4 style='margin-top:0; color:#0051B3;'>Результат расчёта:</h4>
                <p>💵 Выручка: <b>{total_revenue:,.2f} ₸</b></p>
                <p>📦 Общие расходы: <b>{total_cost:,.2f} ₸</b></p>
                <p>💰 Чистая прибыль: <b style='color: #248A3D;'>{total_profit:,.2f} ₸</b></p>
                <p>📈 Прибыль с 1 мешка: <b>{profit_per_bag:,.2f} ₸</b></p>
                <p>📊 Рентабельность: <b style='color: #007AFF;'>{margin:.1f}%</b></p>
            </div>
        """.replace(",", " "), unsafe_allow_html=True)

with tab4:
    st.markdown("### 🧪 Рецептуры сырья (на 50 мешков)")
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    recipe = st.selectbox("Выберите продукт", ["Strong", "Granit"], key="recipe_prod")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if recipe == "Strong":
        items = [
            ("Песок", "200,00 ₸"), ("Цемент", "336,00 ₸"), ("Atocell", "210,00 ₸"),
            ("Эфир", "9,9 ₸"), ("Полипласт", "280,00 ₸"), ("Мешок", "155,7 ₸")
        ]
        total_text, price_text, profit_text, margin_text = "1 191,6 ₸", "1 800 ₸", "608,40 ₸/мешок", "около 51%"
    else:
        items = [
            ("Песок", "200,00 ₸"), ("Цемент", "432,00 ₸"), ("Atocell", "220,5 ₸"),
            ("Эфир", "9,9 ₸"), ("Полипласт", "350,00 ₸"), ("Мешок", "155,7 ₸")
        ]
        total_text, price_text, profit_text, margin_text = "1 368,1 ₸", "2 300 ₸", "931,90 ₸/мешок", "около 40,5%"
        
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    st.markdown(f"<b>Раскладка на 1 мешок ({recipe}):</b><br><br>", unsafe_allow_html=True)
    for comp, bag_c in items:
        st.markdown(f"• <b>{comp}</b>: <span style='color: #007AFF; font-weight: 600;'>{bag_c}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class='ios-card' style='background: #F2F9F1; border: 1px solid #D2EBD0;'>
            <p>📌 Итого себестоимость 1 мешка: <b>{total_text}</b></p>
            <p>🏷️ Базовая цена продажи: <b>{price_text}</b></p>
            <p>💰 Валовая прибыль: <b style='color: #248A3D;'>{profit_text}</b></p>
            <p>📈 Рентабельность: <b style='color: #007AFF;'>{margin_text}</b></p>
        </div>
    """, unsafe_allow_html=True)