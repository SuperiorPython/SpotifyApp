import streamlit as st
import pandas as pd
import altair as alt

def render_genres(PALETTE, PRIMARY, SECONDARY, FILL):
    if "tracks_df" not in st.session_state or "enriched" not in st.session_state:
        st.info("Analyze a playlist to view Genres.")
        return

    tracks_df = st.session_state["tracks_df"]
    enriched  = st.session_state["enriched"]

    # Unique key for this tab
    KEY = "genres_tab_filter"

    # One-time migration from any old key
    if "genre_filter" in st.session_state and KEY not in st.session_state:
        st.session_state[KEY] = st.session_state.pop("genre_filter")

    # Ensure state exists
    if KEY not in st.session_state:
        st.session_state[KEY] = []

    all_genres = (
        enriched.explode("genres")["genres"].dropna().value_counts().head(50).index.tolist()
    )

    # Clear button FIRST (inline handling, no callback)
    clear_col = st.columns([1, 3, 1])[0]
    with clear_col:
        if st.session_state[KEY]:
            if st.button("Clear genre filter", key="genres_clear_btn"):
                st.session_state[KEY] = []
                st.rerun()

    # Multiselect (no default; controlled via state key)
    sel_genres = st.multiselect(
        "Filter by genre (optional)",
        options=all_genres,
        key=KEY,
    )
    selected = sel_genres or st.session_state[KEY]

    filtered = (
        enriched[enriched["genres"].apply(lambda g: any(x in (g or []) for x in selected))]
        if selected else enriched
    )

    st.caption(f"Filtered tracks: {filtered['id'].nunique()} / {tracks_df['id'].nunique()}")

    fg = filtered.explode("genres")
    top_genres = fg["genres"].dropna().value_counts().head(20).reset_index()
    top_genres.columns = ["genre", "count"]

    if not top_genres.empty:
        chart_genres = alt.Chart(top_genres).mark_bar(color=PRIMARY).encode(
            x=alt.X("count:Q", title="Tracks"),
            y=alt.Y("genre:N", sort='-x', title=None),
            tooltip=["genre", "count"],
        ).properties(height=420)
        st.altair_chart(chart_genres, use_container_width=True)
    else:
        st.info("No genre data available for these artists.")
