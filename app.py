import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Mixmann CRM", page_icon="📦", layout="centered")

st.title("📦 Mixmann CRM — Склад")

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

st.markdown("### 💬 Актуальные остатки")

if "Категория" in df.columns and "Наименование" in df.columns:
    categories = df["Категория"].unique()
    
    for cat in categories:
        st.markdown(f"*{cat}*")
        cat_items = df[df["Категория"] == cat]
        
        for _, row in cat_items.iterrows():
            name = row.get("Наименование", "")
            qty = row.get("Количество", 0)
            unit = row.get("Ед. измерения", "")
            st.markdown(f"* {name}: *{qty}* {unit}")
        st.markdown("---")
else:
    st.dataframe(df)

with st.expander("✏️ Изменить остатки на складе"):
    item_list = df["Наименование"].tolist() if "Наименование" in df.columns else []
    if item_list:
        selected_item = st.selectbox("Выберите товар", item_list)
        current_row = df[df["Наименование"] == selected_item].iloc[0]
        
        new_qty = st.number_input("Новое количество", value=float(current_row.get("Количество", 0)))
        
        if st.button("Сохранить изменения"):
            df.loc[df["Наименование"] == selected_item, "Количество"] = new_qty
            df.to_csv(CSV_FILE, index=False)
            st.success(f"Обновлено: {selected_item} — {new_qty}")
            st.rerun()