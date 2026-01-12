import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time

# --- Konfiguracja Strony ---
st.set_page_config(page_title="Magazyn Inteligenty", page_icon="📦", layout="wide")

# --- CSS (Tło i Styl) ---
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-image: linear-gradient(to right top, #fdfcfb, #e2d1c3); }
.stMetric { background-color: rgba(255, 255, 255, 0.4); padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("📦 Inteligentny Magazyn Cloud")
st.caption("Automatyczne sumowanie i precyzyjne zarządzanie ilościami")

# --- Połączenie ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- Logika Bazy Danych ---

def get_products_raw():
    """Pobiera surowe dane produktów do obliczeń"""
    res = supabase.table("produkty").select("*").execute()
    return res.data if res.data else []

def get_categories_dict():
    """Zwraca słownik {nazwa: id}"""
    res = supabase.table("kategorie").select("id, nazwa").execute()
    return {item['nazwa']: item['id'] for item in res.data} if res.data else {}

# --- UI Zakładki ---
tab1, tab2, tab3, tab4 = st.tabs(["📥 Przyjęcie Towaru", "👀 Stan Magazynu", "📊 Statystyki", "⚙️ Zarządzanie"])

# === TAB 1: PRZYJĘCIE (Z SUMOWANIEM) ===
with tab1:
    st.subheader("Dodaj lub uzupełnij towar")
    cat_map = get_categories_dict()
    
    if not cat_map:
        st.warning("Dodaj najpierw kategorię w panelu Supabase lub zakładce Zarządzanie.")
    else:
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Nazwa produktu (dokładna nazwa zsumuje zapas)").strip()
            category_name = col1.selectbox("Kategoria", options=list(cat_map.keys()))
            amount = col2.number_input("Ilość do dodania", min_value=1, step=1)
            price = col2.number_input("Cena jednostkowa (PLN)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("Zaksięguj dostawę", type="primary"):
                if name:
                    # Sprawdź czy produkt o tej nazwie już istnieje
                    existing = supabase.table("produkty").select("*").eq("nazwa", name).execute()
                    
                    if existing.data:
                        # UPDATE: Sumujemy ilości
                        old_id = existing.data[0]['id']
                        new_count = existing.data[0]['liczba'] + amount
                        supabase.table("produkty").update({"liczba": new_count, "cena": price}).eq("id", old_id).execute()
                        st.success(f"Zaktualizowano stan! Obecnie: {new_count} szt.")
                    else:
                        # INSERT: Nowy produkt
                        data = {"nazwa": name, "kategoria": cat_map[category_name], "liczba": amount, "cena": price}
                        supabase.table("produkty").insert(data).execute()
                        st.success(f"Dodano nowy produkt: {name}")
                    
                    time.sleep(1)
                    st.rerun()

# === TAB 2: STAN MAGAZYNU ===
with tab2:
    st.subheader("Aktualne zapasy")
    raw_data = supabase.table("produkty").select("*, kategorie(nazwa)").execute()
    
    if raw_data.data:
        df = pd.DataFrame([
            {
                "ID": i['id'], 
                "Produkt": i['nazwa'], 
                "Kategoria": i['kategorie']['nazwa'] if i['kategorie'] else "Brak",
                "Ilość": i['liczba'], 
                "Cena": i['cena'],
                "Wartość": i['liczba'] * i['cena']
            } for i in raw_data.data
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Magazyn jest pusty.")

# === TAB 3: STATYSTYKI ===
with tab3:
    if raw_data.data:
        df_stats = pd.DataFrame(raw_data.data)
        col1, col2, col3 = st.columns(3)
        col1.metric("Suma sztuk", int(df_stats['liczba'].sum()))
        col2.metric("Wartość netto", f"{(df_stats['liczba'] * df_stats['cena']).sum():.2f} PLN")
        col3.metric("Liczba pozycji", len(df_stats))
        
        st.bar_chart(df_stats, x="nazwa", y="liczba", color="#4F8BF9")

# === TAB 4: ZARZĄDZANIE (USUWANIE ILOŚCI) ===
with tab4:
    st.subheader("Operacje magazynowe")
    
    # 1. ZDEJMOWANIE ZE STANU (Mniejsze ilości)
    st.markdown("### 📉 Wydaj z magazynu (Zdejmij ilość)")
    prods = get_products_raw()
    
    if prods:
        prod_options = {p['nazwa']: p for p in prods}
        selected_p_name = st.selectbox("Wybierz produkt do wydania", options=list(prod_options.keys()))
        current_p = prod_options[selected_p_name]
        
        col_v1, col_v2 = st.columns(2)
        to_remove = col_v1.number_input("Ile sztuk wydać?", min_value=1, max_value=current_p['liczba'], step=1)
        
        if col_v1.button("Potwierdź wydanie"):
            new_qty = current_p['liczba'] - to_remove
            if new_qty > 0:
                supabase.table("produkty").update({"liczba": new_qty}).eq("id", current_p['id']).execute()
                st.toast(f"Wydano {to_remove} szt. Zostało {new_qty}.")
            else:
                # Jeśli 0, usuwamy wiersz
                supabase.table("produkty").delete().eq("id", current_p['id']).execute()
                st.toast(f"Produkt {selected_p_name} został całkowicie wydany i usunięty ze stanu.")
            
            time.sleep(1)
            st.rerun()
    
    st.divider()
    
    # 2. CAŁKOWITE USUWANIE KATEGORII
    st.markdown("### 📂 Zarządzaj kategoriami")
    cats = get_categories_dict()
    if cats:
        cat_to_del = st.selectbox("Usuń całą kategorię", options=list(cats.keys()))
        if st.button("Usuń kategorię"):
            try:
                supabase.table("kategorie").delete().eq("id", cats[cat_to_del]).execute()
                st.success(f"Usunięto {cat_to_del}")
                st.rerun()
            except:
                st.error("Nie można usunąć kategorii, która zawiera produkty!")

    # 3. RESET
    with st.expander("🚨 Opcje krytyczne"):
        if st.button("WYCZYŚĆ CAŁY MAGAZYN"):
            supabase.table("produkty").delete().neq("id", -1).execute()
            st.rerun()
