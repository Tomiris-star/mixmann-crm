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
        padding: 10px 20px;
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

tab1, tab2, tab3 = st.tabs(["Склад", "Прибыль", "Рецептуры"])

with tab1:
    st.markdown("### 📊 Остатки на складе")
    
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

    # Блок стоимости готовой продукции со скриншота
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

    with st.expander("✏️ Изменить остатки товаров"):
        item_list = df["Наименование"].tolist()
        selected_item = st.selectbox("Выберите товар для обновления", item_list)
        current_row = df[df["Наименование"] == selected_item].iloc[0]
        new_qty = st.number_input("Новое количество", value=float(current_row["Количество"]))
        if st.button("Сохранить изменения"):
            df.loc[df["Наименование"] == selected_item, "Количество"] = new_qty
            df.to_csv(CSV_FILE, index=False)
            st.success("Успешно сохранено!")
            st.rerun()

with tab2:
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

with tab3:
    st.markdown("### 🧪 Рецептуры сырья (на 50 мешков)")
    
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    recipe = st.selectbox("Выберите продукт", ["Strong", "Granit"], key="recipe_prod")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if recipe == "Strong":
        items = [
            ("Песок", "200,00 ₸"),
            ("Цемент", "336,00 ₸"),
            ("Atocell", "210,00 ₸"),
            ("Эфир", "9,9 ₸"),
            ("Полипласт", "280,00 ₸"),
            ("Мешок", "155,7 ₸")
        ]
        total_text = "1 191,6 ₸"
        price_text = "1 800 ₸"
        profit_text = "608,40 ₸/мешок"
        margin_text = "около 51%"
    else:
        items = [
            ("Песок", "200,00 ₸"),
            ("Цемент", "432,00 ₸"),
            ("Atocell", "220,5 ₸"),
            ("Эфир", "9,9 ₸"),
            ("Полипласт", "350,00 ₸"),
            ("Мешок", "155,7 ₸")
        ]
        total_text = "1 368,1 ₸"
        price_text = "2 300 ₸"
        profit_text = "931,90 ₸/мешок"
        margin_text = "около 40,5%"
        
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