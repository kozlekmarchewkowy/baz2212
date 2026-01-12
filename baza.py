import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time

# --- Konfiguracja Strony ---
st.set_page_config(
    page_title="Menedżer Produktów",
    page_icon="📦",
    layout="wide" # Zmieniamy układ na szerszy, żeby wykres lepiej wyglądał
)

# --- NIESTANDARDOWE TŁO (CSS) ---
# Wstrzykujemy kod CSS, aby zmienić tło aplikacji.
# Możesz zmienić kolory w 'linear-gradient', aby dopasować je do swoich upodobań.
page_bg_css = """
<style>
[data-testid="stAppViewContainer"] {
background-image: linear-gradient(to right top, #fdfcfb, #e2d1c3);
}

[data-testid="stHeader"] {
background-color: rgba(0,0,0,0);
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

# --- Funkcje Pomocnicze (Pobieranie Danych) ---

# Używamy st.cache_data z krótkim TTL (czasem życia), żeby nie odpytywać bazy ciągle,
# ale jednocześnie mieć w miarę świeże dane.
@st.cache_data(ttl=60)
def get_categories_df():
    """Pobiera kategorie i zwraca jako DataFrame"""
    response = supabase.table("kategorie").select("id, nazwa").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def get_products_flattened():
    """
    Pobiera produkty, łączy z nazwami kategorii i zwraca jako DataFrame.
    Nie cache'ujemy tego tutaj, bo chcemy świeże dane po dodaniu produktu.
    """
    # Składnia select(..., kategorie(nazwa)) wykonuje JOIN w Supabase
    response = supabase.table("produkty").select("*, kategorie(nazwa)").order("id", desc=True).execute()
    
    if response.data:
        # Spłaszczamy strukturę JSON
        flat_data = []
        for item in response.data:
            flat_item = item.copy()
            if item.get('kategorie'):
                 # Wyciągamy nazwę z zagnieżdżonego słownika
                flat_item['kategoria'] = item['kategorie']['nazwa']
            else:
                flat_item['kategoria'] = "Brak (Usunięta?)"
            del flat_item['kategorie'] # usuwamy niepotrzebny już zagnieżdżony obiekt
            flat_data.append(flat_item)
        
        df = pd.DataFrame(flat_data)
        # Zmieniamy kolejność kolumn dla czytelności
        df = df[['id', 'nazwa', 'kategoria', 'liczba', 'cena']]
        return df
    return pd.DataFrame()

# --- Interfejs Użytkownika ---

tab1, tab2, tab3, tab4 = st.tabs(["➕ Dodaj Produkt", "➕ Dodaj Kategorię", "👀 Podgląd Danych", "📊 Statystyki"])

# === TAB 1: DODAWANIE PRODUKTU ===
with tab1:
    st.subheader("Nowy Produkt")
    
    # Pobieramy kategorie jako DataFrame
    cat_df = get_categories_df()
    
    if cat_df.empty:
        st.warning("👉 Najpierw dodaj przynajmniej jedną kategorię w zakładce obok!")
    else:
        # Tworzymy mapę {Nazwa Kategorii: ID Kategorii}
        cat_map = dict(zip(cat_df['nazwa'], cat_df['id']))
        
        with st.form("product_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                 name = st.text_input("Nazwa produktu")
                 # Wybór kategorii z listy nazw
                 selected_cat_name = st.selectbox("Kategoria", options=list(cat_map.keys()))
            with col_b:
                # int8 w bazie -> step=1
                count = st.number_input("Liczba sztuk", min_value=0, step=1, value=1)
                # numeric w bazie -> format float
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
                            "kategoria": cat_map[selected_cat_name] # Przypisujemy ID
                        }
                        supabase.table("produkty").insert(product_data).execute()
                        st.success(f"✅ Dodano produkt: {name}")
                        time.sleep(1) # Krótka pauza, żeby user zobaczył komunikat
                        st.rerun() # Przeładowujemy aplikację, żeby odświeżyć tabele i wykresy
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
                    category_data = {
                        "nazwa": cat_name,
                        "opis": cat_desc
                    }
                    supabase.table("kategorie").insert(category_data).execute()
                    st.success(f"✅ Dodano kategorię: {cat_name}")
                    # Czyścimy cache kategorii, aby nowa pojawiła się w formularzu produktu
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd podczas zapisu: {e}")

# Pobieramy dane o produktach raz, aby użyć ich w Tab 3 i Tab 4
products_df = get_products_flattened()

# === TAB 3: PODGLĄD ===
with tab3:
    st.subheader("Baza produktów")
    if not products_df.empty:
        # Wyświetlamy interaktywny dataframe (można sortować, powiększać)
        st.dataframe(products_df, use_container_width=True, hide_index=True)
    else:
        st.info("Baza produktów jest pusta.")

# === TAB 4: STATYSTYKI I WYKRESY ===
with tab4:
    st.subheader("📊 Analiza magazynu")
    
    if products_df.empty:
        st.info("Dodaj produkty, aby zobaczyć statystyki.")
    else:
        col1, col2 = st.columns(2)
        
        # --- METRYKI ---
        with col1:
            total_products = len(products_df)
            total_stock = products_df['liczba'].sum()
            # Obliczamy wartość magazynu (cena * liczba sztuk)
            total_value = (products_df['cena'] * products_df['liczba']).sum()
            
            st.metric(label="Różnych produktów", value=total_products)
            st.metric(label="Łącznie sztuk w magazynie", value=total_stock)
            st.metric(label="Szacunkowa wartość magazynu", value=f"{total_value:,.2f} PLN".replace(",", " "))

        # --- WYKRES ---
        with col2:
            st.write("**Liczba produktów w kategoriach**")
            # Pandas: grupujemy po kategorii i liczymy wystąpienia
            chart_data = products_df['kategoria'].value_counts().reset_index()
            chart_data.columns = ['Kategoria', 'Liczba produktów']
            
            # Rysujemy wykres słupkowy (bar chart)
            st.bar_chart(
                chart_data,
                x="Kategoria",
                y="Liczba produktów",
                color="#FF4B4B", # Przykładowy kolor słupków
                use_container_width=True
            )
