# src/views/genres.py
import pandas as pd
import altair as alt
import streamlit as st

# Fallback palette; remove if you import from a shared theme/constants
PRIMARY = "#43a047"

def render_genres(PALETTE, PRIMARY, SECONDARY, FILL):
    """Genres tab: filterable genre bar chart + filtered track count."""
    # Guard
    if "tracks_df" not in st.session_state or "enriched" not in st.session_state:
        st.info("Analyze a playlist to view Genres.")
        return

    tracks_df = st.session_state["tracks_df"]
    enriched  = st.session_state["enriched"]

    # Ensure session filter key exists (persists across reruns)
    if "genre_filter" not in st.session_state:
        st.session_state["genre_filter"] = []

    # Build genre list (top 50 by occurrence)
    if "genres" in enriched.columns:
        gexp = enriched.explode("genres")
        all_genres = (
            gexp["genres"].dropna().astype(str).value_counts().head(50).index.tolist()
        )
    else:
        all_genres = []

    # Multiselect filter
    sel_genres = st.multiselect(
        "Filter by genre (optional)",
        options=all_genres,
        key="genre_filter",
        placeholder="Start typing a genre…",
    )

    # Filter rows by selected genres
    if sel_genres:
        filtered = enriched[
            enriched["genres"].apply(lambda g: any(x in (g or []) for x in sel_genres))
        ]
    else:
        filtered = enriched

    st.caption(
        f"Filtered tracks: {int(filtered['id'].nunique())} / {int(tracks_df['id'].nunique())}"
    )

    # Top 20 genres within the filtered set
    if "genres" in filtered.columns:
        fg = filtered.explode("genres")
        top_genres = (
            fg["genres"].dropna().astype(str).value_counts().head(20).reset_index()
        )
        top_genres.columns = ["genre", "count"]
    else:
        top_genres = pd.DataFrame(columns=["genre", "count"])

    if not top_genres.empty:
        chart = (
            alt.Chart(top_genres)
            .mark_bar(color=PRIMARY)
            .encode(
                x=alt.X("count:Q", title="Tracks"),
                y=alt.Y("genre:N", sort='-x', title=None),
                tooltip=["genre:N", "count:Q"],
            )
            .properties(height=420)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No genre data available for these artists.")

    # Optional: small UX helper to clear filter
    clear_col = st.columns([1, 3, 1])[0]
    with clear_col:
        if sel_genres and st.button("Clear genre filter"):
            st.session_state["genre_filter"] = []
            st.experimental_rerun()
