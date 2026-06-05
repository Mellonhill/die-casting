import streamlit as st
import pandas as pd
from config import settings
from data.fetchers import patent_fetcher

st.set_page_config(page_title="Die Casting Patent Analytics", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")

if "patents" not in st.session_state:
    st.session_state.patents = []
if "filters" not in st.session_state:
    st.session_state.filters = {"material": ["Zama","Alluminio","Magnesio"], "year_range": (settings.default_year_start, settings.default_year_end), "status": ["granted","pending","expired","unknown"]}

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/patent.png", width=60)
    st.title("🔍 Filtri Globali")
    material_filter = st.multiselect("Materiale/i", ["Zama","Alluminio","Magnesio"], default=st.session_state.filters["material"])
    year_range = st.slider("Anni di deposito", 2000, 2030, st.session_state.filters["year_range"], step=1)
    status_filter = st.multiselect("Stato legale", ["granted","pending","expired","unknown"], default=st.session_state.filters["status"])
    refresh_btn = st.button("🔄 Aggiorna dati", use_container_width=True)
    st.session_state.filters["material"] = material_filter
    st.session_state.filters["year_range"] = year_range
    st.session_state.filters["status"] = status_filter

@st.cache_data(ttl=3600)
def load_patents_data(material_list, year_start, year_end, force=False):
    all_patents = []
    for mat in material_list:
        all_patents.extend(patent_fetcher.fetch_patents(mat, year_start, year_end, force_refresh=force))
    return all_patents

if refresh_btn or not st.session_state.patents:
    with st.spinner("Caricamento brevetti in corso..."):
        st.session_state.patents = load_patents_data(
            st.session_state.filters["material"],
            st.session_state.filters["year_range"][0],
            st.session_state.filters["year_range"][1],
            force=refresh_btn
        )

filtered_patents = [p for p in st.session_state.patents if p.status in st.session_state.filters["status"]]
st.sidebar.markdown(f"**Brevetti visualizzati:** {len(filtered_patents)}")

st.markdown("<h1 style='text-align: center;'>🏭 Die Casting Patent Intelligence</h1><p style='text-align: center;'>Analisi brevettuale per Zama, Alluminio e Magnesio</p>", unsafe_allow_html=True)
st.info("📌 Seleziona una pagina dal menu a sinistra per iniziare l'analisi.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Totale brevetti", len(filtered_patents))
col2.metric("Zama", sum(1 for p in filtered_patents if p.material_category == "Zama"))
col3.metric("Alluminio", sum(1 for p in filtered_patents if p.material_category == "Alluminio"))
col4.metric("Magnesio", sum(1 for p in filtered_patents if p.material_category == "Magnesio"))

if filtered_patents:
    df_preview = pd.DataFrame([{"ID": p.id, "Titolo": p.title[:60], "Materiale": p.material_category, "Data": p.filing_date} for p in filtered_patents[:5]])
    st.dataframe(df_preview, use_container_width=True)