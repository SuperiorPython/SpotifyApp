import streamlit as st
import pandas as pd
import altair as alt

def render_overview(PALETTE, PRIMARY, SECONDARY, FILL):
    st.set_page_config(layout="wide", initial_sidebar_state="expanded")

    if ("tracks_df" not in st.session_state) or ("enriched" not in st.session_state):
        st.info("Paste a public playlist and analyze to begin.")
        return

    meta = st.session_state["meta"]
    tracks_df = st.session_state["tracks_df"]
    enriched  = st.session_state["enriched"]

    st.caption(f"📃 Playlist: **{meta['name']}** by **{meta['owner']}**  •  Usable tracks: {len(tracks_df)}  •  Dropped: {meta['dropped']}")

    cA, cB, cC = st.columns(3)
    cA.metric("Tracks analyzed", tracks_df["id"].nunique())
    unique_artists = enriched.get("artist_name", pd.Series(dtype=str)).nunique() or tracks_df["artist"].nunique()
    cB.metric("Unique artists", int(unique_artists))
    cC.metric("Median popularity", int(tracks_df["popularity"].median() if not tracks_df.empty else 0))

    # sample
    N_PREVIEW = 15
    idxs = st.session_state.get("preview_idx", list(tracks_df.index))
    preview_df = tracks_df.loc[idxs[:min(N_PREVIEW, len(idxs))]]
    with st.expander(f"Show random sample ({len(preview_df)})"):
        st.dataframe(preview_df[["name","artist","album","release_year","popularity"]],
                     use_container_width=True, hide_index=True)

    # donut genres
    g_exploded = enriched.explode("genres")
    genre_counts = g_exploded["genres"].dropna().value_counts().head(12).reset_index()
    genre_counts.columns = ["genre","count"]
    st.subheader("Genre footprint (top 12)")
    if not genre_counts.empty:
        donut = (
            alt.Chart(genre_counts)
            .encode(
                theta=alt.Theta("count:Q", stack=True),
                color=alt.Color("genre:N", legend=None, scale=alt.Scale(range=PALETTE)),
                order=alt.Order("count:Q", sort="descending"),
                tooltip=["genre:N","count:Q"]
            )
            .mark_arc(innerRadius=120, outerRadius=220, stroke="white", strokeWidth=1)
            .properties(width=520, height=520)
        )
        st.altair_chart(donut, use_container_width=True)
    else:
        st.info("No genre data available for a donut chart.")
