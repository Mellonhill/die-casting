import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
from main import filtered_patents
from analysis.trends import compute_yearly_counts, get_top_applicants

st.set_page_config(layout="wide")
st.title("📊 Dashboard Panoramica")
patents = filtered_patents
if not patents:
    st.warning("Nessun brevetto trovato.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Totale", len(patents))
col2.metric("Zama", sum(1 for p in patents if p.material_category == "Zama"))
col3.metric("Alluminio", sum(1 for p in patents if p.material_category == "Alluminio"))
col4.metric("Magnesio", sum(1 for p in patents if p.material_category == "Magnesio"))

yearly = compute_yearly_counts(patents)
if not yearly.empty:
    st.plotly_chart(px.line(yearly, x="year", y="count", color="material", title="Andamento depositi per anno", markers=True), use_container_width=True)

top_apps = get_top_applicants(patents, n=10)
if not top_apps.empty:
    data = []
    for p in patents:
        for app in p.applicants:
            if app.name in top_apps["name"].values and p.filing_date:
                data.append({"applicant": app.name, "year": p.filing_date.year})
    if data:
        pivot = pd.DataFrame(data).groupby(["applicant","year"]).size().unstack(fill_value=0)
        st.plotly_chart(px.imshow(pivot, text_auto=True, aspect="auto", title="Heatmap Depositanti × Anno"), use_container_width=True)

countries = [app.country for p in patents for app in p.applicants if app.country]
if countries:
    country_counts = Counter(countries)
    map_df = pd.DataFrame({"country": list(country_counts.keys()), "count": list(country_counts.values())})
    st.plotly_chart(px.choropleth(map_df, locations="country", locationmode="country names", color="count", title="Distribuzione geografica"), use_container_width=True)
else:
    st.info("Nessuna informazione paese disponibile.")