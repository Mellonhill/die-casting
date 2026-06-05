import streamlit as st
import plotly.express as px
from main import filtered_patents
from analysis.trends import aggregate_trends, year_over_year_growth

st.title("📈 Trend Brevettuali")
patents = filtered_patents
if not patents:
    st.warning("Nessun dato.")
    st.stop()

trend = aggregate_trends(patents)
yearly = trend["trend"]
if yearly.empty:
    st.warning("Dati annuali insufficienti.")
    st.stop()

fig_main = px.line(yearly, x="year", y="count", color="material", title="Numero depositi per anno e materiale")
for w in [3,5]:
    col = f"ma_{w}y"
    if col in yearly.columns:
        for mat in yearly["material"].unique():
            mask = yearly["material"] == mat
            fig_main.add_scatter(x=yearly[mask]["year"], y=yearly[mask][col], mode="lines", name=f"{mat} MA{w}", line=dict(dash="dot"))
st.plotly_chart(fig_main, use_container_width=True)

growth = year_over_year_growth(yearly.copy())
if "growth_pct" in growth.columns:
    pivot = growth.pivot(index="year", columns="material", values="growth_pct").round(1)
    st.subheader("Crescita % Anno su Anno")
    st.dataframe(pivot.style.format("{:.1f}%"))

if not trend["seasonal"].empty:
    fig_season = px.bar(trend["seasonal"], x="month", y="count", color="material", facet_col="material", title="Stagionalità mensile")
    st.plotly_chart(fig_season, use_container_width=True)