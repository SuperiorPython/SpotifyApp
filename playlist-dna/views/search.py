# views/search.py
from __future__ import annotations
from pathlib import Path
import streamlit as st
import pandas as pd
import altair as alt
import numpy as np



def _genres_for_track(enriched: pd.DataFrame, track_id: str) -> list[str]:
    g = (
        enriched.loc[enriched["id"] == track_id, "genres"]
        .explode()
        .dropna()
        .astype(str)
        .str.strip()
    )
    # keep order by frequency, then alpha
    counts = g.value_counts()
    ordered = (
        counts.sort_values(ascending=False)
        .index.tolist()
    )
    return ordered[:20]  # cap for display


def _percentile(series: pd.Series, value: float) -> float:
    if series.empty:
        return 0.0
    return (series <= value).mean() * 100.0


def render_search(PALETTE, PRIMARY, SECONDARY, FILL):
    if "tracks_df" not in st.session_state or "enriched" not in st.session_state:
        st.info("Analyze a playlist to use Search.")
        return

    tracks_df: pd.DataFrame = st.session_state["tracks_df"].copy()
    enriched: pd.DataFrame = st.session_state["enriched"].copy()

    st.subheader("Search a track in this playlist")

    # Build a searchable label: "Song — Artist"
    tracks_df["label"] = tracks_df.apply(
        lambda r: f"{r.get('name','—')} — {r.get('artist','—')}", axis=1
    )

    # --- Search box (reruns on each keystroke) ---
    q = st.text_input(
        "Search by song or artist",
        placeholder="e.g., Circles or Post Malone",
        key="search_q",
    )

    # Filter matches (case-insensitive on name or artist)
    if q:
        mask = (
                tracks_df["name"].str.contains(q, case=False, na=False)
                | tracks_df["artist"].str.contains(q, case=False, na=False)
        )
        matches = tracks_df[mask].copy()
    else:
        matches = tracks_df.copy()

    # Build labels and take top N for suggestion list
    matches["label"] = matches.apply(lambda r: f"{r.get('name', '—')} — {r.get('artist', '—')}", axis=1)
    suggestions = matches.head(10)[["label", "id"]].reset_index(drop=True)

    if suggestions.empty:
        st.warning("No matches. Try a different keyword.")
        st.stop()

    # Show a light “autocomplete” list that updates as you type
    picked_label = st.radio(
        "Suggestions",
        options=suggestions["label"].tolist(),
        index=0,
        key="search_suggestions",
    )

    # Resolve the selected row
    sel = suggestions.loc[suggestions["label"] == picked_label].iloc[0]
    tid = sel["id"]
    row = tracks_df.loc[tracks_df["id"] == tid].iloc[0]

    # Gather more details
    genres = _genres_for_track(enriched, tid)
    release_year = row.get("release_year")
    popularity = int(row.get("popularity", 0) or 0)
    added_at = row.get("added_at")
    album = row.get("album", "—")
    link = row.get("url")
    image = row.get("image")

    # Layout
    left, right = st.columns([1, 2])

    with left:
        if image:
            st.image(image, use_container_width=True)
        if link:
            st.markdown(f"[Open in Spotify]({link})")

    with right:
        # --- Song stats (refined) ---
        st.markdown("### 🧠 Song Stats")

        # Core values
        tid = row["id"]
        release_year = row.get("release_year")
        popularity = int(row.get("popularity", 0) or 0)
        added_at = row.get("added_at")

        # Order added (by timestamp)
        pos = None
        if "added_at" in tracks_df and tracks_df["added_at"].notna().any() and pd.notna(added_at):
            t_sorted = tracks_df.dropna(subset=["added_at"]).sort_values("added_at").reset_index(drop=True)
            idx = t_sorted.index[t_sorted["id"] == tid]
            if len(idx) > 0:
                pos = int(idx[0]) + 1

        # Age
        age = None
        if pd.notna(release_year):
            from datetime import datetime
            try:
                age = datetime.now().year - int(release_year)
            except Exception:
                age = None

        # Playlist popularity stats
        avg_pop = int(tracks_df["popularity"].mean()) if "popularity" in tracks_df else None
        median_pop = int(tracks_df["popularity"].median()) if "popularity" in tracks_df else None

        # Genre keywords (no chart)
        track_genres = (
            enriched.loc[enriched["id"] == tid, "genres"]
            .explode().dropna().astype(str).str.strip().unique().tolist()
        )
        genre_keywords = ", ".join(track_genres[:10]) if track_genres else "—"

        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Popularity", f"{popularity}/100")
        c2.metric("Median Popularity (playlist)", median_pop or "—")
        c3.metric("Order Added", f"#{pos}" if pos else "—")

        c4, c5, c6 = st.columns(3)
        c4.metric("Release Year", release_year if pd.notna(release_year) else "—")
        c5.metric("Song Age", f"{age} yrs" if age is not None else "—")
        c6.metric("Date Added", pd.to_datetime(added_at).date().isoformat() if pd.notna(added_at) else "—")

        # --- Popularity distribution with highlighted bin marker ---
        if "popularity" in tracks_df and not tracks_df["popularity"].isna().all():

            # Bin playlist popularities into 20 uniform bins (0–100 by 5s)
            pop_series = tracks_df["popularity"].dropna().astype(float)
            bins = list(range(0, 101, 2))  # 0,5,10,...,100 (20 bins)
            labels = [f"{b}-{b + 5}" for b in bins[:-1]]
            centers = [b + 2.5 for b in bins[:-1]]

            binned = pd.cut(pop_series, bins=bins, right=False, labels=centers)  # label by bin center
            hist = binned.value_counts().rename_axis("center").reset_index(name="count")
            hist["center"] = hist["center"].astype(float)

            # Find this track's bin center & count
            track_center = float((popularity // 5) * 5 + 2.5)
            track_row = hist.loc[hist["center"] == track_center]
            track_count = int(track_row["count"].iloc[0]) if not track_row.empty else 0

            # --- Popularity Histogram ---
            bars = (
                alt.Chart(tracks_df.dropna(subset=["popularity"]))
                .mark_bar(color=PRIMARY, opacity=0.8)
                .encode(
                    x=alt.X(
                        "popularity:Q",
                        bin=alt.Bin(maxbins=20),
                        title="Popularity (0–100)"
                    ),
                    y=alt.Y("count():Q", title="Tracks"),
                    tooltip=[alt.Tooltip("count():Q", title="Tracks")]
                )
            )

            # --- Highlight marker anchored at bottom ---
            highlight_df = pd.DataFrame({
                "popularity": [popularity],
                "count": [0]  # force baseline alignment
            })
            highlight = (
                alt.Chart(highlight_df)
                .mark_point(
                    shape="circle",
                    size=180,
                    filled=True,
                    color="#00e676"
                )
                .encode(
                    x="popularity:Q",
                    y=alt.Y("count:Q")
                )
            )

            # --- Combine ---
            st.altair_chart(
                (bars + highlight).properties(height=240),
                use_container_width=True
            )

        # Genre keywords (chips)
        st.markdown("#### Genre Keywords")
        if track_genres:
            st.markdown(
                """
                <style>
                .chips { display:flex; flex-wrap:wrap; gap:8px; margin:6px 0 2px 0; }
                .chip { padding:4px 10px; border-radius:999px; background:#1b5e20; color:#e8f5e9; font-size:12px; border:1px solid #2e7d32;}
                </style>
                """,
                unsafe_allow_html=True
            )
            st.markdown(
                '<div class="chips">' + "".join(
                    [f'<span class="chip">{g}</span>' for g in track_genres[:16]]) + "</div>",
                unsafe_allow_html=True
            )
        else:
            st.caption("No genres available for this track.")


    st.markdown("### Raw Data")
    # Raw details table (optional)
    with st.expander("Raw track details"):
        show_cols = ["name", "artist", "album", "release_year", "popularity", "added_at", "id", "url"]
        st.dataframe(tracks_df.loc[[row.name], [c for c in show_cols if c in tracks_df.columns]], use_container_width=True)


