import streamlit as st
from supabase import create_client, Client

# --- Konfiguracja Strony ---
st.set_page_config(page_title="Menedżer Produktów", layout="centered")
st.title("📦 Menedżer Bazy Danych")

# --- Połączenie z Supabase ---
# Używamy st.cache_resource, aby nie łączyć się przy każdym kliknięciu
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- Funkcje Pomocnicze ---
def get_categories():
    """Pobiera listę kategorii do selectboxa"""
    response = supabase.table("kategorie").select("id, nazwa").execute()
    return response.data

# --- Interfejs Użytkownika ---

tab1, tab2, tab3 = st.tabs(["➕ Dodaj Produkt", "➕ Dodaj Kategorię", "👀 Podgląd Danych"])

# === TAB 1: DODAWANIE PRODUKTU ===
with tab1:
    st.header("Nowy Produkt")
    
    # Pobieramy kategorie, aby użytkownik mógł wybrać nazwę, a nie wpisywać ID ręcznie
    categories_data = get_categories()
    
    if not categories_data:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię w zakładce obok!")
    else:
        # Tworzymy słownik {Nazwa Kategorii: ID Kategorii}
        cat_map = {item['nazwa']: item['id'] for item in categories_data}
        
        with st.form("product_form", clear_on_submit=True):
            name = st.text_input("Nazwa produktu")
            col1, col2 = st.columns(2)
            with col1:
                # int8 w bazie -> step=1
                count = st.number_input("Liczba sztuk", min_value=0, step=1)
            with col2:
                # numeric w bazie -> format float
                price = st.number_input("Cena", min_value=0.0, format="%.2f")
            
            # Wybór kategorii z listy
            selected_cat_name = st.selectbox("Kategoria", options=list(cat_map.keys()))
            
            submitted = st.form_submit_button("Zapisz produkt")
            
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
                        st.success(f"Dodano produkt: {name}")
                    except Exception as e:
                        st.error(f"Błąd podczas zapisu: {e}")

# === TAB 2: DODAWANIE KATEGORII ===
with tab2:
    st.header("Nowa Kategoria")
    
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
                    st.success(f"Dodano kategorię: {cat_name}")
                    # Czyścimy cache, aby nowa kategoria pojawiła się od razu w zakładce produktów
                    st.cache_data.clear() 
                except Exception as e:
                    st.error(f"Błąd podczas zapisu: {e}")

# === TAB 3: PODGLĄD ===
with tab3:
    st.subheader("Ostatnio dodane produkty")
    # Pobieramy produkty i łączymy z tabelą kategorii, żeby wyświetlić nazwę kategorii zamiast ID
    try:
        response = supabase.table("produkty").select("*, kategorie(nazwa)").order("id", desc=True).limit(10).execute()
        if response.data:
            # Spłaszczamy strukturę danych do wyświetlenia
            flat_data = []
            for item in response.data:
                flat_item = item.copy()
                if item.get('kategorie'):
                    flat_item['kategoria_nazwa'] = item['kategorie']['nazwa']
                else:
                    flat_item['kategoria_nazwa'] = "Brak"
                del flat_item['kategorie'] # usuwamy zagnieżdżony obiekt
                flat_data.append(flat_item)
                
            st.dataframe(flat_data)
        else:
            st.info("Baza produktów jest pusta.")
    except Exception as e:
        st.error(f"Nie udało się pobrać danych: {e}")
