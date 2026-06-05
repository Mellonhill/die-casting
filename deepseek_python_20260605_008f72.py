import streamlit as st
import plotly.express as px
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile
from main import filtered_patents
from analysis.trends import get_top_applicants

st.title("🏢 Competitor Intelligence")
patents = filtered_patents
if not patents:
    st.warning("Nessun dato.")
    st.stop()

top_df = get_top_applicants(patents, n=15)
if not top_df.empty:
    fig_top = px.bar(top_df.head(15), x="total", y="name", orientation="h", title="Top Depositanti")
    st.plotly_chart(fig_top, use_container_width=True)
    selected = st.selectbox("Seleziona depositante", top_df["name"].head(10))
    if selected:
        patents_app = [p for p in patents if any(a.name == selected for a in p.applicants)]
        cpc_counts = {}
        for p in patents_app:
            for cpc in p.cpc_classes:
                sub = cpc[:4]
                cpc_counts[sub] = cpc_counts.get(sub, 0) + 1
        if cpc_counts:
            df_cpc = pd.DataFrame({"CPC Subclass": list(cpc_counts.keys()), "Count": list(cpc_counts.values())})
            st.plotly_chart(px.treemap(df_cpc, path=["CPC Subclass"], values="Count", title=f"Portfolio - {selected}"), use_container_width=True)

st.subheader("🤝 Rete di collaborazioni")
G = nx.Graph()
for p in patents[:100]:
    invs = p.inventors
    for i in range(len(invs)):
        for j in range(i+1, len(invs)):
            G.add_edge(invs[i], invs[j])
if G.number_of_nodes() > 0:
    net = Network(height="500px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        with open(tmp.name, "r", encoding="utf-8") as f:
            st.components.v1.html(f.read(), height=550)
else:
    st.info("Nessuna collaborazione rilevata.")

all_cpc = [cpc[:4] for p in patents for cpc in p.cpc_classes]
if all_cpc:
    cpc_series = pd.Series(all_cpc).value_counts().head(8)
    st.plotly_chart(px.pie(values=cpc_series.values, names=cpc_series.index, hole=0.4, title="Market share per sottoclasse CPC"), use_container_width=True)