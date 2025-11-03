# src/views/time.py
import pandas as pd
import altair as alt
import streamlit as st

# Fallback colors; swap for your centralized theme if you have one
PALETTE  = ["#1b5e20","#2e7d32","#388e3c","#43a047","#4caf50","#66bb6a","#81c784","#a5d6a7","#c8e6c9"]
FILL     = "#66bb6a"

def render_time(PALETTE, PRIMARY, SECONDARY, FILL):
    """Time tab: decade timeline + Artist × Year heatmap."""
    if "tracks_df" not in st.session_state or "enriched" not in st.session_state:
        st.info("Analyze a playlist to view Time visuals.")
        return

    tracks_df: pd.DataFrame = st.session_state["tracks_df"]
    enriched: pd.DataFrame  = st.session_state["enriched"]

    # --- Timeline by decade ---
    st.subheader("Timeline by decade")
    td = tracks_df.dropna(subset=["release_year"]).copy()
    if not td.empty:
        td["decade"] = (td["release_year"] // 10) * 10
        decade_counts = td.groupby("decade").size().reset_index(name="count")

        if not decade_counts.empty:
            area = (
                alt.Chart(decade_counts)
                .mark_area(opacity=0.7, color=FILL)
                .encode(
                    x=alt.X("decade:O", title="Decade"),
                    y=alt.Y("count:Q", title="Tracks"),
                    tooltip=[alt.Tooltip("decade:O", title="Decade"), alt.Tooltip("count:Q", title="Tracks")],
                )
                .properties(height=260)
            )
            st.altair_chart(area, use_container_width=True)
        else:
            st.info("No release year data available.")
    else:
        st.info("No release year data available.")

    # --- Artist × Year heatmap ---
    st.subheader("Artist × Year heatmap")
    if not td.empty:
        ay = enriched.dropna(subset=["release_year"]).copy()
        if ay.empty or "artist" not in ay.columns:
            st.info("Not enough data for heatmap.")
            return

        # Lead artist (first credited)
        ay["lead_artist"] = ay["artist"].astype(str).str.split(", ").str[0]

        # Control: how many artists to show
        top_n = st.slider("How many artists to include", 6, 24, 12, 1, help="Top artists by track count")
        topN_artists = ay["lead_artist"].value_counts().head(top_n).index.tolist()
        ay = ay[ay["lead_artist"].isin(topN_artists)]

        if ay.empty:
            st.info("Not enough year data for heatmap.")
            return

        heat = (
            alt.Chart(ay)
            .mark_rect()
            .encode(
                x=alt.X("release_year:O", title="Year"),
                y=alt.Y("lead_artist:N", sort='-x', title="Artist"),
                color=alt.Color("count():Q", title="Tracks", scale=alt.Scale(range=PALETTE[::-1])),
                tooltip=[
                    alt.Tooltip("lead_artist:N", title="Artist"),
                    alt.Tooltip("release_year:O", title="Year"),
                    alt.Tooltip("count():Q", title="Tracks"),
                ],
            )
            .properties(height=340)
        )
        st.altair_chart(heat, use_container_width=True)
    else:
        st.info("Not enough year data for heatmap.")
