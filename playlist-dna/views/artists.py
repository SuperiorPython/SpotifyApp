# src/views/artists.py
import pandas as pd
import altair as alt
import streamlit as st

PRIMARY = "#43a047"  # keep in sync with your theme

def render_artists(PALETTE, PRIMARY, SECONDARY, FILL):
    """Artists tab: lollipop chart of top lead artists by track appearances."""
    if "enriched" not in st.session_state:
        st.info("Analyze a playlist to view Artists.")
        return

    enriched: pd.DataFrame = st.session_state["enriched"]
    if enriched.empty or "artist" not in enriched.columns:
        st.info("No artist data available.")
        return

    # Derive lead artist (first credited)
    lead = enriched.copy()
    lead["lead_artist"] = lead["artist"].astype(str).str.split(", ").str[0]

    # Control: how many to show
    top_n = st.slider("How many artists to show", 5, 50, 25, 1)

    counts = (
        lead["lead_artist"]
        .value_counts()
        .head(top_n)
        .reset_index()
        .rename(columns={"index": "artist", "lead_artist": "count"})  # value_counts reset
    )
    counts.columns = ["artist", "count"]  # ensure exact names

    st.caption(f"Top artists by track appearances (lead artist, top {top_n})")

    if counts.empty:
        st.info("No artists found.")
        return

    # Lollipop chart
    base = alt.Chart(counts).encode(
        y=alt.Y("artist:N", sort='-x', title=None)
    )

    stems = base.mark_rule(color="#a5d6a7").encode(
        x=alt.X("count:Q", title="Tracks"),
        x2=alt.value(0),
    )

    hover = alt.selection_point(fields=["artist"], on="mouseover", nearest=True, empty=False)

    dots = (
        base
        .add_params(hover)
        .mark_circle(color=PRIMARY, opacity=0.95)
        .encode(
            x="count:Q",
            size=alt.condition(hover, alt.value(600), alt.value(220)),
            tooltip=[alt.Tooltip("artist:N", title="Artist"), alt.Tooltip("count:Q", title="Tracks")],
        )
    )

    chart = (stems + dots).properties(height=max(300, 20 * len(counts)))
    st.altair_chart(chart, use_container_width=True)
