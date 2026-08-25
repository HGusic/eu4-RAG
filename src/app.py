"""Streamlit UI: retrieve wiki chunks, then answer with Ollama."""

from __future__ import annotations

import streamlit as st

from generate import MODEL, generate_stream
from retrieve import retrieve

st.set_page_config(page_title="EU4 Wiki RAG", layout="wide")
st.title("EU4 Wiki RAG")
st.caption("Answers are grounded in locally indexed Europa Universalis 4 wiki chunks.")

question = st.text_input(
    "Question",
    placeholder="How is advisor hiring cost calculated?",
)
k = st.slider("Chunks to retrieve", 3, 8, 5)

if st.button("Ask") and question.strip():
    with st.spinner("Searching wiki chunks…"):
        hits = retrieve(question.strip(), k=k)
    st.markdown("### Answer")
    try:
        st.write_stream(generate_stream(question.strip(), hits))
    except Exception as exc:
        st.error(
            f"Ollama did not respond (model={MODEL}). "
            "Install Ollama, run `ollama pull llama3.1`, and keep it running. "
            f"({exc})"
        )
    st.markdown("### Sources")
    for hit in hits:
        with st.expander(f"{hit['title']} — {hit['section']}  (distance={hit['distance']:.3f})"):
            st.markdown(f"[Wiki]({hit['url']})")
            st.write(hit["text"][:3000])
