# src/views/evolution.py
import pandas as pd
import altair as alt
import streamlit as st

# Fallback palette if you don't import from a shared theme module
PALETTE  = ["#1b5e20","#2e7d32","#388e3c","#43a047","#4caf50","#66bb6a","#81c784","#a5d6a7","#c8e6c9"]
PRIMARY  = "#43a047"
FILL     = "#66bb6a"

def render_evolution(PALETTE, PRIMARY, SECONDARY, FILL):
    """Evolution tab: growth curve, genre-over-time, weekday×hour heatmap."""
    if "tracks_df" not in st.session_state or "enriched" not in st.session_state:
        st.info("Analyze a playlist to see its evolution over time.")
        return

    tracks_df = st.session_state["tracks_df"].copy()
    enriched  = st.session_state["enriched"].copy()

    # guard for added_at
    if "added_at" not in tracks_df or tracks_df["added_at"].isna().all():
        st.info("This playlist has no `added_at` timestamps available.")
        return

    # ---- Common time keys ----
    t = tracks_df.dropna(subset=["added_at"]).copy()
    # ensure timezone-naive for Altair
    t["date"]    = t["added_at"].dt.tz_convert(None).dt.date
    t["month"]   = t["added_at"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()
    t["weekday"] = t["added_at"].dt.tz_convert(None).dt.day_name()
    t["hour"]    = t["added_at"].dt.tz_convert(None).dt.hour

    # ---- 1) Growth curve (cumulative tracks over time) ----
    st.subheader("Playlist growth over time")

    growth = (
        t.groupby("date").size().reset_index(name="added").sort_values("date")
    )
    growth["cumulative"] = growth["added"].cumsum()

    area = (
        alt.Chart(growth)
        .mark_area(color=FILL, opacity=0.25)
        .encode(
            x=alt.X("date:T", title="Date added"),
            y=alt.Y("cumulative:Q", title="Total tracks"),
            tooltip=["date:T", "added:Q", "cumulative:Q"],
        )
    )
    line = (
        alt.Chart(growth)
        .mark_line(color=PRIMARY, strokeWidth=3)
        .encode(x="date:T", y="cumulative:Q")
    )
    st.altair_chart((area + line).properties(height=280), use_container_width=True)

    # ---- 2) Genre evolution (stacked area by month, top 8) ----
    st.subheader("Genre footprint over time (top 8)")

    g = enriched.dropna(subset=["added_at"]).copy()
    g["month"] = g["added_at"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()
    g = g.explode("genres")
    g["genres"] = g["genres"].fillna("unknown")

    if not g.empty:
        topK = g["genres"].value_counts().head(8).index.tolist()
        g_top = g[g["genres"].isin(topK)]
        genre_month = (
            g_top.groupby(["month","genres"]).size().reset_index(name="count").sort_values("month")
        )
        if not genre_month.empty:
            area = (
                alt.Chart(genre_month)
                .mark_area(opacity=0.85)
                .encode(
                    x=alt.X("month:T", title="Month added"),
                    y=alt.Y("count:Q", stack="normalize", title="Share of tracks"),
                    color=alt.Color("genres:N", title="Genre", scale=alt.Scale(range=PALETTE)),
                    tooltip=["month:T","genres:N","count:Q"],
                )
                .properties(height=320)
            )
            st.altair_chart(area, use_container_width=True)
        else:
            st.info("Not enough genre data to show evolution.")
    else:
        st.info("Not enough genre data to show evolution.")

    # ---- 3) Activity heatmap (weekday × hour) ----
    st.subheader("When are tracks added? (weekday × hour)")
    wh = t.groupby(["weekday","hour"]).size().reset_index(name="count")
    if not wh.empty:
        weekday_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        heat = (
            alt.Chart(wh)
            .mark_rect()
            .encode(
                x=alt.X("hour:O", title="Hour of day (0–23)"),
                y=alt.Y("weekday:N", sort=weekday_order, title=None),
                color=alt.Color("count:Q", title="Tracks", scale=alt.Scale(range=PALETTE[::-1])),
                tooltip=["weekday:N","hour:O","count:Q"],
            )
            .properties(height=220)
        )
        st.altair_chart(heat, use_container_width=True)
    else:
        st.info("Not enough timestamp data for activity heatmap.")

