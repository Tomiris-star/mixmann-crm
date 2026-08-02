import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Mixmann CRM", page_icon="📦", layout="centered")

st.title("📦 Mixmann CRM — Управление")

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

tab1, tab2, tab3 = st.tabs(["📋 Склад", "💰 Калькулятор прибыли", "🧪 Рецептуры и сырьё"])

with tab1:
    st.markdown("### Актуальные остатки")
    if "Категория" in df.columns and "Наименование" in df.columns:
        categories = df["Категория"].unique()
        for cat in categories:
            st.markdown(f"*{cat}*")
            cat_items = df[df["Категория"] == cat]
            for _, row in cat_items.iterrows():
                name = str(row.get("Наименование", ""))
                qty = str(row.get("Количество", ""))
                unit = str(row.get("Ед. измерения", ""))
                st.markdown(f"- {name}: *{qty} {unit}*")
            st.markdown("---")
    else:
        st.dataframe(df)

    with st.expander("✏️ Изменить остатки"):
        item_list = df["Наименование"].tolist() if "Наименование" in df.columns else []
        if item_list:
            selected_item = st.selectbox("Выберите товар", item_list)
            current_row = df[df["Наименование"] == selected_item].iloc[0]
            new_qty = st.number_input("Новое количество", value=float(current_row.get("Количество", 0)))
            if st.button("Сохранить"):
                df.loc[df["Наименование"] == selected_item, "Количество"] = new_qty
                df.to_csv(CSV_FILE, index=False)
                st.success("Обновлено!")
                st.rerun()

with tab2:
    st.markdown("### 📊 Расчёт прибыли и рентабельности")
    
    product = st.selectbox("Выберите продукт", ["Strong", "Granit"])
    
    if product == "Strong":
        cost_per_bag = 1191.60
        default_price = 1800.0
    else:
        cost_per_bag = 1368.10
        default_price = 2300.0
        
    st.markdown(f"Себестоимость 1 мешка ({product}): *{cost_per_bag:,.2f} ₸*".replace(",", " "))
    
    selling_price = st.number_input("Отпускная цена за 1 мешок (₸)", value=default_price, step=50.0)
    bags_count = st.number_input("Количество мешков", value=50, step=10)
    
    if st.button("Рассчитать маржу"):
        total_revenue = selling_price * bags_count
        total_cost = cost_per_bag * bags_count
        total_profit = total_revenue - total_cost
        profit_per_bag = selling_price - cost_per_bag
        margin = (profit_per_bag / cost_per_bag) * 100 if cost_per_bag > 0 else 0
        
        st.markdown("---")
        st.markdown(f"- 💵 *Выручка:* {total_revenue:,.2f} ₸".replace(",", " "))
        st.markdown(f"- 📦 *Себестоимость общая:* {total_cost:,.2f} ₸".replace(",", " "))
        st.markdown(f"- 💰 *Чистая прибыль:* *{total_profit:,.2f} ₸*".replace(",", " "))
        st.markdown(f"- 📈 *Прибыль с 1 мешка:* {profit_per_bag:,.2f} ₸".replace(",", " "))
        st.markdown(f"- 📊 *Рентабельность:* *{margin:.1f}%*")

with tab3:
    st.markdown("### 🧪 Детализация сырья (на 50 мешков)")
    
    recipe = st.selectbox("Рецептура продукта", ["Strong", "Granit"])
    
    if recipe == "Strong":
        df_rec = pd.DataFrame({
            "Компонент": ["Песок", "Цемент", "Atocell 1240", "Эфир крахмала", "Полипласт РПП", "Мешок"],
            "Общая стоимость": ["10 000 ₸", "16 800 ₸", "10 500 ₸", "495 ₸", "14 000 ₸", "—"],
            "На 1 мешок": ["200,00 ₸", "336,00 ₸", "210,00 ₸", "9,90 ₸", "280,00 ₸", "155,70 ₸"]
        })
        total_text = "1 191,60 ₸"
        price_text = "1 800 ₸"
        profit_text = "608,40 ₸/мешок"
        margin_text = "около 51%"
    else:
        df_rec = pd.DataFrame({
            "Компонент": ["Песок", "Цемент", "Atocell 1240", "Эфир крахмала", "Полипласт РПП", "Мешок"],
            "Общая стоимость": ["10 000 ₸", "21 600 ₸", "11 025 ₸", "495 ₸", "17 500 ₸", "—"],
            "На 1 мешок": ["200,00 ₸", "432,00 ₸", "220,50 ₸", "9,90 ₸", "350,00 ₸", "155,70 ₸"]
        })
        total_text = "1 368,10 ₸"
        price_text = "2 300 ₸"
        profit_text = "931,90 ₸/мешок"
        margin_text = "около 40,5%"
    
    st.table(df_rec)
    st.markdown(f"*Итого себестоимость одного мешка:* {total_text}")
    st.markdown("---")
    st.markdown(f"Если отпускная цена *{recipe}* — *{price_text} / мешок*, то:")
    st.markdown(f"- Валовая прибыль: *{profit_text}*")
    st.markdown(f"- Рентабельность: *{margin_text}*")