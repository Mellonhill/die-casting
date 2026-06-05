import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from io import BytesIO
from main import filtered_patents

st.title("🔎 Ricerca & Filtro Brevetti")
patents = filtered_patents
if not patents:
    st.warning("Nessun brevetto.")
    st.stop()

df = pd.DataFrame([{
    "ID": p.id, "Titolo": p.title, "Abstract": p.abstract[:200]+"...",
    "Inventori": ", ".join(p.inventors[:3]), "Depositante": p.applicants[0].name if p.applicants else "N/A",
    "Anno": p.filing_date.year if p.filing_date else "", "Paese": p.country_code,
    "Status": p.status, "Materiale": p.material_category, "CPC": ", ".join(p.cpc_classes[:3])
} for p in patents])

col1, col2 = st.columns(2)
with col1:
    search = st.text_input("🔍 Cerca in titolo/abstract")
    mat_sel = st.multiselect("Materiale", df["Materiale"].unique(), default=df["Materiale"].unique())
with col2:
    stat_sel = st.multiselect("Stato", df["Status"].unique(), default=df["Status"].unique())
    year_range = st.slider("Anno", int(df["Anno"].min()), int(df["Anno"].max()), (int(df["Anno"].min()), int(df["Anno"].max())))

mask = (df["Materiale"].isin(mat_sel)) & (df["Status"].isin(stat_sel)) & (df["Anno"].between(year_range[0], year_range[1]))
if search:
    mask &= (df["Titolo"].str.contains(search, case=False) | df["Abstract"].str.contains(search, case=False))
filtered_df = df[mask]
st.subheader(f"Risultati: {len(filtered_df)} brevetti")

gb = GridOptionsBuilder.from_dataframe(filtered_df)
gb.configure_pagination(paginationAutoPageSize=True)
gb.configure_side_bar()
gb.configure_selection('single')
grid = AgGrid(filtered_df, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, fit_columns_on_grid_load=True, theme="streamlit")

if grid["selected_rows"] is not None and len(grid["selected_rows"]) > 0:
    sel_id = grid["selected_rows"].iloc[0]["ID"]
    patent = next((p for p in patents if p.id == sel_id), None)
    if patent:
        with st.expander("📄 Dettaglio brevetto", expanded=True):
            st.markdown(f"**Titolo:** {patent.title}")
            st.markdown(f"**Abstract:** {patent.abstract}")
            st.markdown(f"**Inventori:** {', '.join(patent.inventors)}")
            st.markdown(f"**Depositanti:** {', '.join([a.name for a in patent.applicants])}")
            st.markdown(f"**Link Espacenet:** [Clicca qui](https://worldwide.espacenet.com/patent/search?q={patent.id})")

if st.button("📥 Esporta CSV"):
    st.download_button("Scarica CSV", filtered_df.to_csv(index=False).encode('utf-8'), "brevetti.csv", "text/csv")
if st.button("📊 Esporta Excel"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, sheet_name="Brevetti", index=False)
    st.download_button("Scarica Excel", output.getvalue(), "brevetti.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")