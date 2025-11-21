# src/views/covers.py
import pandas as pd
import streamlit as st

def render_covers(PALETTE, PRIMARY, SECONDARY, FILL):
    """Covers tab: neat grid of album arts with stable order per analysis."""
    if "tracks_df" not in st.session_state:
        st.info("Analyze a playlist to view covers.")
        return

    tracks_df: pd.DataFrame = st.session_state["tracks_df"]
    thumbs_all = tracks_df.dropna(subset=["image"]).copy()

    if thumbs_all.empty:
        st.info("No cover art found for this playlist.")
        return

    st.caption("Album covers (neatly aligned)")

    # Controls (optional)
    total_available = len(thumbs_all)
    max_show = min(100, total_available)  # safety cap
    count = st.slider("How many covers to show", 12, max_show, min(24, max_show), step=6)
    n_cols = st.slider("Columns", 3, 10, 6, step=1)

    # Stable randomized order per analyze, falls back if not present
    idxs = st.session_state.get("covers_idx", list(thumbs_all.index))
    thumbs = thumbs_all.loc[idxs[:min(count, len(idxs))]].reset_index(drop=True)

    cols = st.columns(n_cols, gap="small")
    for i, row in thumbs.iterrows():
        with cols[i % n_cols]:
            st.image(row["image"], use_container_width=True)
