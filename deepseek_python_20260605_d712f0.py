import streamlit as st
import plotly.express as px
import pandas as pd
from main import filtered_patents
from analysis.risk import compute_fto_score, track_expiring_patents, cpc_heatmap_data, identify_white_spaces, compute_citation_network

st.title("⚠️ IP Risk & White Space")
patents = filtered_patents
if not patents:
    st.warning("Nessun brevetto.")
    st.stop()

with st.spinner("Calcolo FTO scores..."):
    fto = [compute_fto_score(p) for p in patents[:100]]
    st.subheader("Freedom-to-Operate Score (rischio)")
    st.dataframe(pd.DataFrame([s.model_dump() for s in fto]).sort_values("score", ascending=False).head(10))

expiring = track_expiring_patents(patents, [1,3,5])
st.subheader("⏳ Brevetti in scadenza")
for w, lst in expiring.items():
    st.write(f"**Entro {w} anni:** {len(lst)} brevetti")
    if lst:
        st.dataframe(pd.DataFrame([{"ID": p.id, "Titolo": p.title, "Scadenza": p.expiry_date} for p in lst[:5]]))

cpc_pivot = cpc_heatmap_data(patents)
if not cpc_pivot.empty:
    st.subheader("🌡️ Heatmap copertura CPC")
    st.plotly_chart(px.imshow(cpc_pivot, text_auto=True, aspect="auto", labels=dict(x="Materiale", y="CPC subclass")), use_container_width=True)
    white = identify_white_spaces(cpc_pivot, threshold=1)
    if white:
        st.subheader("✅ White Space (aree con poca protezione)")
        for sub, mats in white[:10]:
            st.write(f"- **{sub}**: opportunità per {', '.join(mats)}")

citations = compute_citation_network(patents)
st.subheader("📖 Citazioni")
st.metric("Totale citazioni forward", citations["total_citations"])
if citations["most_cited"]:
    st.write("Brevetti più citati:")
    for pid, cnt in citations["most_cited"][:5]:
        st.write(f"  - {pid}: {cnt} citazioni")