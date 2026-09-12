"""CRYPTOZEN Forensic Dashboard — Streamlit entry point."""
import streamlit as st

from src.config import Config
from src.generator import DatasetGenerator
from src.graph_engine import GraphEngine
from src.ml_engine import MLEngine
from ui import pages
from ui.theme import inject_css, logo_html

st.set_page_config(
    page_title="CRYPTOZEN — Forensic Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner="Building dataset + graph + ML models...")
def load_pipeline():
    cfg = Config("config.yaml")
    data = DatasetGenerator(cfg).generate()
    graph = GraphEngine(data)
    feat = graph.extract_features()
    ml = MLEngine(cfg)
    scored = ml.run(feat)
    return data, scored, graph


def main():
    inject_css()
    data, feat, graph = load_pipeline()

    with st.sidebar:
        st.markdown(logo_html(), unsafe_allow_html=True)

        if "page" not in st.session_state:
            st.session_state.page = "dashboard"

        for key, (label, _) in pages.PAGES.items():
            active = st.session_state.page == key
            prefix = "▸ " if active else "   "
            if st.button(f"{prefix}{label}", key=f"nav-{key}",
                         use_container_width=True):
                st.session_state.page = key
                st.rerun()

    _, render = pages.PAGES[st.session_state.page]
    render(data, feat, graph)


if __name__ == "__main__":
    main()