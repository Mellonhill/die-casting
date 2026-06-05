import streamlit as st
import plotly.express as px
import pandas as pd
from main import filtered_patents
from analysis.clustering import cluster_patents, compute_lda, generate_wordcloud

st.title("🧠 Technology Clustering (NLP)")
patents = filtered_patents
if len(patents) < 5:
    st.warning("Servono almeno 5 brevetti.")
    st.stop()

with st.spinner("Elaborazione clustering..."):
    cluster = cluster_patents(patents)
    lda = compute_lda(patents, n_topics=8)

if cluster["labels"]:
    st.subheader("📌 Cluster K-Means")
    emb = cluster["embedding"]
    if emb is not None and len(emb) > 0:
        df_plot = pd.DataFrame({"x": emb[:,0], "y": emb[:,1], "cluster": cluster["labels"].astype(str), "id": cluster["ids"]})
        st.plotly_chart(px.scatter(df_plot, x="x", y="y", color="cluster", hover_data=["id"], title="Proiezione UMAP"), use_container_width=True)
    st.subheader("☁️ WordCloud per cluster")
    cluster_texts = {}
    for i, label in enumerate(cluster["labels"]):
        cluster_texts.setdefault(label, []).append(cluster["texts"][i])
    sel_clust = st.selectbox("Seleziona cluster", sorted(cluster_texts.keys()))
    if sel_clust in cluster_texts:
        fig = generate_wordcloud(cluster_texts[sel_clust], title=f"Cluster {sel_clust}")
        st.pyplot(fig)

if lda["topics"]:
    st.subheader("📚 Topic Modeling (LDA)")
    for t in lda["topics"]:
        st.markdown(f"**Topic {t['topic_id']+1}:** {', '.join(t['keywords'][:8])}")
    if lda["doc_topic"] is not None:
        st.dataframe(pd.DataFrame(lda["doc_topic"], columns=[f"Topic {i+1}" for i in range(lda["doc_topic"].shape[1])]).head(10))