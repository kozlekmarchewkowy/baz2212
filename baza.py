import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time

# --- Konfiguracja Strony ---
st.set_page_config(
    page_title="Menedżer Produktów",
    page_icon="📦",
    layout="wide"
)

# --- NIESTANDARDOWE TŁO (CSS) ---
page_bg_css = """
<style>
[data-testid="stAppViewContainer"] {
background-image: linear-gradient(to right top, #fdfcfb, #e2d1c3);
}
[data-testid="stHeader"] {
background-color: rgba(0,0,0,0);
}
/* Stylizacja przycisków w ekspanderach */
div.stButton > button {
    width: 100%;
}
</style>
"""
st.markdown(page_bg_css, unsafe_allow_html=True)

# --- Tytuł ---
st.title("📦 Magazyn Cloud")
st.markdown("---")

# --- Połączenie z Supabase ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except FileNotFoundError:
        st.error("Brak pliku secrets.toml lub nie skonfigurowano sekretów na Streamlit Cloud.")
        st.stop()

supabase = init_connection()

# --- Funkcje Pomocnicze ---
def get_categories_data():
    """Pobiera kategorie jako listę słowników (bez cache dla delete)"""
    response = supabase.table("kategorie").select("id, nazwa").order("nazwa").execute()
    return response.data if response.data else []

def get_products_data():
    """Pobiera produkty jako listę słowników (bez cache dla delete)"""
    response = supabase.table("produkty").select("id, nazwa").order("nazwa").execute()
    return response.data if response.data else []

@st.cache_data(ttl=60)
def get_categories_df():
    response = supabase.table("kategorie").select("id, nazwa").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def get_products_flattened():
    response = supabase.table("produkty").select("*, kategorie(nazwa)").order("id", desc=True).execute()
    if response.data:
        flat_data = []
        for item in response.data:
            flat_item = item.copy()
            if item.get('kategorie'):
                flat_item['kategoria'] = item['kategorie']['nazwa']
            else:
                flat_item['kategoria'] = "Brak (Usunięta?)"
            del flat_item['kategorie']
            flat_data.append(flat_item)
        
        df = pd.DataFrame(flat_data)
        if not df.empty:
            df = df[['id', 'nazwa', 'kategoria', 'liczba', 'cena']]
        return df
    return pd.DataFrame()

# --- Interfejs Użytkownika ---

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ Dodaj Produkt", 
    "➕ Dodaj Kategorię", 
    "👀 Podgląd Danych", 
    "📊 Statystyki",
    "⚙️ Zarządzanie"
])

# Pobieramy dane globalnie dla zakładek podglądu
cat_df = get_categories_df()
products_df = get_products_flattened()

# === TAB 1: DODAWANIE PRODUKTU ===
with tab1:
    st.subheader("Nowy Produkt")
    
    if cat_df.empty:
        st.warning("👉 Najpierw dodaj przynajmniej jedną kategorię w zakładce obok!")
    else:
        cat_map = dict(zip(cat_df['nazwa'], cat_df['id']))
        
        with st.form("product_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                 name = st.text_input("Nazwa produktu")
                 selected_cat_name = st.selectbox("Kategoria", options=list(cat_map.keys()))
            with col_b:
                count = st.number_input("Liczba sztuk", min_value=0, step=1, value=1)
                price = st.number_input("Cena (PLN)", min_value=0.0, format="%.2f")
            
            submitted = st.form_submit_button("Zapisz produkt", type="primary")
            
            if submitted:
                if not name:
                    st.error("Podaj nazwę produktu.")
                else:
                    try:
                        product_data = {
                            "nazwa": name,
                            "liczba": int(count),
                            "cena": float(price),
                            "kategoria": cat_map[selected_cat_name]
                        }
                        supabase.table("produkty").insert(product_data).execute()
                        st.success(f"✅ Dodano produkt: {name}")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd podczas zapisu: {e}")

# === TAB 2: DODAWANIE KATEGORII ===
with tab2:
    st.subheader("Nowa Kategoria")
    with st.form("category_form", clear_on_submit=True):
        cat_name = st.text_input("Nazwa kategorii")
        cat_desc = st.text_area("Opis kategorii")
        submitted_cat = st.form_submit_button("Zapisz kategorię")
        
        if submitted_cat:
            if not cat_name:
                st.error("Nazwa kategorii jest wymagana.")
            else:
                try:
                    category_data = {"nazwa": cat_name, "opis": cat_desc}
                    supabase.table("kategorie").insert(category_data).execute()
                    st.success(f"✅ Dodano kategorię: {cat_name}")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd podczas zapisu: {e}")

# === TAB 3: PODGLĄD ===
with tab3:
    st.subheader("Baza produktów")
    if not products_df.empty:
        st.dataframe(products_df, use_container_width=True, hide_index=True)
    else:
        st.info("Baza produktów jest pusta.")

# === TAB 4: STATYSTYKI ===
with tab4:
    st.subheader("📊 Analiza magazynu")
    if products_df.empty:
        st.info("Dodaj produkty, aby zobaczyć statystyki.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            total_products = len(products_df)
            total_stock = products_df['liczba'].sum()
            total_value = (products_df['cena'] * products_df['liczba']).sum()
            st.metric(label="Różnych produktów", value=total_products)
            st.metric(label="Łącznie sztuk w magazynie", value=total_stock)
            st.metric(label="Szacunkowa wartość", value=f"{total_value:,.2f} PLN".replace(",", " "))
        with col2:
            st.write("**Liczba produktów w kategoriach**")
            chart_data = products_df['kategoria'].value_counts().reset_index()
            chart_data.columns = ['Kategoria', 'Liczba produktów']
            st.bar_chart(chart_data, x="Kategoria", y="Liczba produktów", color="#FF4B4B", use_container_width=True)

# === TAB 5: ZARZĄDZANIE I USUWANIE ===
with tab5:
    st.header("⚙️ Zarządzanie zasobami")
    
    col_mgmt_1, col_mgmt_2 = st.columns(2)
    
    # --- SEKCJA 1: USUWANIE PRODUKTÓW ---
    with col_mgmt_1:
        st.info("🗑️ **Usuwanie produktów**")
        all_products = get_products_data()
        
        if not all_products:
            st.write("Brak produktów do usunięcia.")
        else:
            # Tworzymy słownik { "ID: Nazwa" : ID } dla selectboxa
            prod_options = {f"{p['id']}: {p['nazwa']}": p['id'] for p in all_products}
            
            selected_prods_to_del = st.multiselect(
                "Wybierz produkty do usunięcia:",
                options=list(prod_options.keys())
            )
            
            if st.button("Usuń wybrane produkty"):
                if not selected_prods_to_del:
                    st.warning("Wybierz przynajmniej jeden produkt.")
                else:
                    try:
                        # Pobieramy listę ID do usunięcia
                        ids_to_delete = [prod_options[name] for name in selected_prods_to_del]
                        
                        # Supabase 'in_' pozwala usunąć wiele ID na raz
                        supabase.table("produkty").delete().in_("id", ids_to_delete).execute()
                        
                        st.success(f"Usunięto {len(ids_to_delete)} produktów.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd: {e}")

    # --- SEKCJA 2: USUWANIE KATEGORII ---
    with col_mgmt_2:
        st.info("📂 **Usuwanie kategorii**")
        all_cats = get_categories_data()
        
        if not all_cats:
            st.write("Brak kategorii.")
        else:
            cat_options = {f"{c['nazwa']}": c['id'] for c in all_cats}
            
            selected_cat_to_del = st.selectbox(
                "Wybierz kategorię do usunięcia:",
                options=list(cat_options.keys())
            )
            
            if st.button("Usuń kategorię"):
                try:
                    cat_id = cat_options[selected_cat_to_del]
                    supabase.table("kategorie").delete().eq("id", cat_id).execute()
                    
                    st.success(f"Usunięto kategorię: {selected_cat_to_del}")
                    st.cache_data.clear() # Czyścimy cache, bo lista kategorii się zmieniła
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    # Supabase zwróci błąd, jeśli kategoria ma przypisane produkty (Foreign Key)
                    st.error("❌ Nie można usunąć tej kategorii!")
                    st.warning("Prawdopodobnie istnieją produkty przypisane do tej kategorii. Usuń je najpierw lub przenieś do innej kategorii.")

    st.divider()
    
    # --- SEKCJA 3: STREFA NIEBEZPIECZNA ---
    with st.expander("🔥 Strefa Niebezpieczna (Reset Bazy)"):
        st.error("Ta akcja usunie **WSZYSTKIE** produkty z bazy danych.")
        confirm_delete = st.checkbox("Rozumiem ryzyko i chcę wyczyścić cały magazyn")
        
        if st.button("WYCZYŚĆ CAŁY MAGAZYN", disabled=not confirm_delete):
            try:
                supabase.table("produkty").delete().neq("id", -1).execute()
                st.toast("Magazyn został wyczyszczony!", icon="🗑️")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")
