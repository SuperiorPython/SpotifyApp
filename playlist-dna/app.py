# app.py
import os, time
from pathlib import Path
import streamlit as st
import pandas as pd
import altair as alt

# --- App config ---
st.set_page_config(
    page_title="Playlist DNA",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded"  # start with sidebar hidden
)

APP_DIR = Path(__file__).resolve().parent
COVER_PATH = APP_DIR / "assets" / "cover_image.png"
st.image(str(COVER_PATH))

# --- Theme palette (shared) ---
PALETTE = ["#1b5e20","#2e7d32","#388e3c","#43a047","#4caf50",
           "#66bb6a","#81c784","#a5d6a7","#c8e6c9"]
PRIMARY, SECONDARY, FILL = "#43a047", "#2e7d32", "#66bb6a"

# --- Local imports (after sys.path is already fine for Streamlit) ---
from src.ui.cover import render_cover
from src.core.auth import build_spotify_client, spotify_call
from src.core.fetch import extract_playlist_id, get_playlist_meta, fetch_playlist_tracks, fetch_artists_details
from src.core.stats import compute_stats, compute_evolution_stats, pick_openai_model, llm_vibe_summary_detailed, build_rule_based_summary

def need_analysis():
    return ("tracks_df" not in st.session_state) or ("enriched" not in st.session_state)


if need_analysis() and not st.session_state.get("trigger_analyze"):                     # 👈 hide sidebar on cover only
    render_cover("assets/cover_image.png", size_px=450)
    st.stop()
# --- Spotify client ---
sp = build_spotify_client()

#def need_analysis():
    #return ("tracks_df" not in st.session_state) or ("enriched" not in st.session_state)

# --- Sidebar (only after analysis) ---
with st.sidebar:
    if not need_analysis():
        if st.button("🔄 Choose Another Playlist", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key not in ("market",):  # keep market if you want
                    del st.session_state[key]
            st.session_state["trigger_analyze"] = False
            st.rerun()
        st.divider()
        if st.button("🔄 Clear cache & rerun", use_container_width=True):
            st.cache_data.clear()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# --- Cover gate ---
#if need_analysis() and not st.session_state.get("trigger_analyze"):
#    render_cover("assets/cover_image.png")  # sets trigger + url and reruns
#    st.stop()

# --- Analyze trigger (runs after cover or sidebar request) ---
if st.session_state.get("trigger_analyze"):
    _url = st.session_state.get("cover_playlist_url", "")
    pid = extract_playlist_id(_url)
    if not pid:
        st.error("Please paste a valid **public** playlist link/URI (or a 22-char ID).")
        st.stop()

    with st.status("Analyzing playlist…", state="running") as status:
        try:
            status.update(label="Fetching metadata…")
            meta = get_playlist_meta(sp, pid, market=st.session_state.get("market","US"))
            owner = (meta.get("owner") or {}).get("display_name", "unknown")
            pname = meta.get("name", "(no name)")

            status.update(label="Fetching tracks…")
            tracks_df, dropped = fetch_playlist_tracks(sp, pid, market=st.session_state.get("market","US"))
            tracks_df["added_at"] = pd.to_datetime(tracks_df["added_at"], errors="coerce", utc=True)
            tracks_df["added_by_name"] = tracks_df.get("added_by_name", pd.Series(["unknown"]*len(tracks_df))).fillna("").replace("", "unknown")
            if tracks_df.empty:
                st.error("No usable tracks (playlist may be episodes/local/region-blocked). Try another.")
                st.stop()

            status.update(label="Enriching artists/genres…")
            all_artist_ids = [aid for lst in tracks_df["artist_ids"].dropna().tolist() for aid in (lst or [])]
            artists_df = fetch_artists_details(sp, all_artist_ids)

            enriched = tracks_df.explode("artist_ids").rename(columns={"artist_ids":"artist_id"})
            if not artists_df.empty:
                enriched = enriched.merge(artists_df, on="artist_id", how="left")
            else:
                enriched["artist_name"] = enriched["artist"].str.split(", ").str[0]
                enriched["genres"] = [[] for _ in range(len(enriched))]
                enriched["artist_popularity"] = None

            # persist
            st.session_state["last_pid"] = pid
            st.session_state["meta"] = {"name": pname, "owner": owner, "dropped": dropped}
            st.session_state["tracks_df"] = tracks_df
            st.session_state["enriched"] = enriched

            # stable preview/covers order
            seed = int(time.time())
            st.session_state["preview_idx"] = tracks_df.sample(frac=1, random_state=seed).index.tolist()
            st.session_state["covers_idx"]  = tracks_df.dropna(subset=["image"]).sample(frac=1, random_state=seed).index.tolist()

            st.session_state.pop("trigger_analyze", None)
            status.update(label="Done ✅", state="complete")
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

# --- Views (tabs) ---
from views.overview import render_overview
from views.evolution import render_evolution
from views.genres import render_genres
from views.artists import render_artists
from views.time import render_time
from views.popularity import render_popularity
from views.covers import render_covers
from views.companion import render_companion
from views.export import render_export

TABS = ["Overview","Evolution","Genres","Artists","Time","Popularity","Covers","Companion (AI)","Export"]
tab_over, tab_evo, tab_gen, tab_art, tab_time, tab_pop, tab_cov, tab_ai, tab_export = st.tabs(TABS)

with tab_over:     render_overview(PALETTE, PRIMARY, SECONDARY, FILL)
with tab_evo:      render_evolution(PALETTE, PRIMARY, SECONDARY, FILL)
with tab_gen:      render_genres(PALETTE, PRIMARY, SECONDARY, FILL)
with tab_art:      render_artists(PALETTE, PRIMARY, SECONDARY, FILL)
with tab_time:     render_time(PALETTE, PRIMARY, SECONDARY, FILL)
with tab_pop:      render_popularity(PALETTE, PRIMARY, SECONDARY, FILL)
with tab_cov:      render_covers(PALETTE, PRIMARY, SECONDARY, FILL)
with tab_ai:       render_companion(PALETTE, PRIMARY, SECONDARY, FILL)
with tab_export:   render_export()
