import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Mixmann CRM", page_icon="📦", layout="centered")

# Применяем стили интерфейса под iOS
st.markdown("""
    <style>
    .stApp {
        background-color: #F2F2F7;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
    }
    h1, h2, h3 {
        color: #000000;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    /* Стилизация вкладок */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #E5E5EA;
        padding: 4px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #3A3A3C;
        font-weight: 600;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    </style>
""", unsafe_allow_html=True)

st.title("Mixmann CRM")

CSV_FILE = "МойСклад - Склад.csv"

@st.cache_data
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        data = {
            "Категория": ["Готовая продукция", "Готовая продукция", "Сырьё и материалы", "Пустые мешки"],
            "Наименование": ["Strong", "Клей", "Песок", "ШВС"],
            "Количество": [24, 4, 21, 3702],
            "Ед. измерения": ["мешка", "п (поддонов)", "т", "шт"],
            "Стоимость/Примечание": ["43.200 тг", "230.400 тг", "0 тг", "0 тг"]
        }
        df = pd.DataFrame(data)
        df.to_csv(CSV_FILE, index=False)
        return df

df = load_data()

tab1, tab2, tab3 = st.tabs(["Склад", "Прибыль", "Рецептуры"])

with tab1:
    st.markdown("### Сводка склада")
    
    # Выводим данные в виде красивых карточек-списков без таблиц
    if "Категория" in df.columns and "Наименование" in df.columns:
        categories = df["Категория"].unique()
        for cat in categories:
            st.markdown(f"#### 🔹 {cat}")
            cat_items = df[df["Категория"] == cat]
            for _, row in cat_items.iterrows():
                name = str(row.get("Наименование", ""))
                qty = str(row.get("Количество", ""))
                unit = str(row.get("Ед. измерения", ""))
                st.markdown(f"• *{name}*: {qty} {unit}")
            st.markdown("---")
    
    with st.expander("✏️ Изменить остатки"):
        item_list = df["Наименование"].tolist() if "Наименование" in df.columns else []
        if item_list:
            selected_item = st.selectbox("Выберите товар", item_list)
            current_row = df[df["Наименование"] == selected_item].iloc[0]
            new_qty = st.number_input("Новое количество", value=float(current_row.get("Количество", 0)))
            if st.button("Сохранить изменения"):
                df.loc[df["Наименование"] == selected_item, "Количество"] = new_qty
                df.to_csv(CSV_FILE, index=False)
                st.success("Успешно обновлено!")
                st.rerun()

with tab2:
    st.markdown("### Калькулятор прибыли")
    
    product = st.selectbox("Продукт", ["Strong", "Granit"])
    
    if product == "Strong":
        cost_per_bag = 1191.60
        default_price = 1800.0
    else:
        cost_per_bag = 1368.10
        default_price = 2300.0
        
    st.markdown(f"Себестоимость 1 мешка: *{cost_per_bag:,.2f} ₸*".replace(",", " "))
    
    selling_price = st.number_input("Цена продажи за 1 мешок (₸)", value=default_price, step=50.0)
    bags_count = st.number_input("Количество мешков", value=50, step=10)
    
    if st.button("Рассчитать"):
        total_revenue = selling_price * bags_count
        total_cost = cost_per_bag * bags_count
        total_profit = total_revenue - total_cost
        profit_per_bag = selling_price - cost_per_bag
        margin = (profit_per_bag / cost_per_bag) * 100 if cost_per_bag > 0 else 0
        
        st.markdown("---")
        st.markdown(f"💵 Выручка: *{total_revenue:,.2f} ₸*".replace(",", " "))
        st.markdown(f"📦 Себестоимость: *{total_cost:,.2f} ₸*".replace(",", " "))
        st.markdown(f"💰 Чистая прибыль: *{total_profit:,.2f} ₸*".replace(",", " "))
        st.markdown(f"📈 Прибыль с 1 мешка: *{profit_per_bag:,.2f} ₸*".replace(",", " "))
        st.markdown(f"📊 Рентабельность: *{margin:.1f}%*")

with tab3:
    st.markdown("### Рецептуры и сырьё")
    
    recipe = st.selectbox("Выберите продукт", ["Strong", "Granit"])
    
    if recipe == "Strong":
        items = [
            ("Песок", "10 000 ₸", "200,00 ₸"),
            ("Цемент", "16 800 ₸", "336,00 ₸"),
            ("Atocell 1240", "10 500 ₸", "210,00 ₸"),
            ("Эфир крахмала", "495 ₸", "9,90 ₸"),
            ("Полипласт РПП", "14 000 ₸", "280,00 ₸"),
            ("Мешок", "—", "155,70 ₸")
        ]
        total_text = "1 191,60 ₸"
        price_text = "1 800 ₸"
        profit_text = "608,40 ₸/мешок"
        margin_text = "около 51%"
    else:
        items = [
            ("Песок", "10 000 ₸", "200,00 ₸"),
            ("Цемент", "21 600 ₸", "432,00 ₸"),
            ("Atocell 1240", "11 025 ₸", "220,50 ₸"),
            ("Эфир крахмала", "495 ₸", "9,90 ₸"),
            ("Полипласт РПП", "17 500 ₸", "350,00 ₸"),
            ("Мешок", "—", "155,70 ₸")
        ]
        total_text = "1 368,10 ₸"
        price_text = "2 300 ₸"
        profit_text = "931,90 ₸/мешок"
        margin_text = "около 40,5%"
    
    st.markdown(f"*Состав на 50 мешков ({recipe}):*")
    for comp, total_c, bag_c in items:
        st.markdown(f"- *{comp}: общая {total_c} | на 1 мешок: *{bag_c}**")
    
    st.markdown("---")
    st.markdown(f"📌 *Итого себестоимость 1 мешка:* *{total_text}*")
    st.markdown(f"Если продавать по *{price_text}*: ")
    st.markdown(f"- Валовая прибыль: *{profit_text}*")
    st.markdown(f"- Рентабельность: *{margin_text}*")