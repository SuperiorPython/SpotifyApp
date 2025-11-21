# src/views/popularity.py
import pandas as pd
import altair as alt
import streamlit as st

PRIMARY   = "#43a047"
SECONDARY = "#2e7d32"

def render_popularity(PALETTE, PRIMARY, SECONDARY, FILL):
    """Popularity tab: histogram of popularity + popularity vs. year/decade."""
    if "tracks_df" not in st.session_state:
        st.info("Analyze a playlist to view Popularity.")
        return

    tracks_df: pd.DataFrame = st.session_state["tracks_df"]

    # --- Popularity histogram ---
    st.subheader("Popularity distribution")
    pop = tracks_df.dropna(subset=["popularity"]).copy()
    if pop.empty:
        st.info("No popularity data available.")
    else:
        bins = st.slider("Bins", min_value=8, max_value=40, value=20, step=1, help="Histogram bin count")
        chart_pop = (
            alt.Chart(pop)
            .mark_bar(color=PRIMARY)
            .encode(
                x=alt.X("popularity:Q", bin=alt.Bin(maxbins=bins), title="Popularity (0–100)"),
                y=alt.Y("count():Q", title="Tracks"),
                tooltip=[alt.Tooltip("count():Q", title="Tracks")],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_pop, use_container_width=True)

    # --- Popularity vs. time ---
    st.subheader("Popularity vs. time")
    td2 = tracks_df.dropna(subset=["release_year", "popularity"]).copy()
    if td2.empty:
        st.info("No release years available for scatter plot.")
        return

    # Let users choose year granularity
    granularity = st.radio(
        "Time granularity", ["Year", "Decade"], horizontal=True, index=0
    )

    if granularity == "Decade":
        td2["decade"] = (td2["release_year"] // 10) * 10
        x_field = alt.X("decade:O", title="Decade")
    else:
        x_field = alt.X("release_year:O", title="Year")

    pop_scatter = (
        alt.Chart(td2)
        .mark_circle(color=SECONDARY, opacity=0.75)
        .encode(
            x=x_field,
            y=alt.Y("popularity:Q", title="Popularity"),
            size=alt.Size("count():Q", legend=None),
            tooltip=[
                alt.Tooltip("name:N", title="Track"),
                alt.Tooltip("artist:N", title="Artist"),
                alt.Tooltip("album:N", title="Album"),
                alt.Tooltip("release_year:O", title="Year"),
                alt.Tooltip("popularity:Q", title="Popularity"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(pop_scatter, use_container_width=True)
