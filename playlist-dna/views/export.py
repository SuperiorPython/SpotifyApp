# src/views/export.py
import io
import json
import pandas as pd
import streamlit as st

def _serialize_genres(series: pd.Series, mode: str = "json") -> pd.Series:
    """Turn list-like genres into a string for export."""
    if mode == "json":
        return series.apply(lambda g: json.dumps(g) if isinstance(g, (list, tuple)) else json.dumps([] if pd.isna(g) else g))
    if mode == "pipe":
        return series.apply(lambda g: "|".join(g) if isinstance(g, (list, tuple)) else ("" if pd.isna(g) else str(g)))
    return series.astype(str)

def render_export():
    """Export tab: download tracks + artists as CSV/Parquet."""
    if "tracks_df" not in st.session_state or "enriched" not in st.session_state:
        st.info("Analyze a playlist to export data.")
        return

    tracks_df: pd.DataFrame = st.session_state["tracks_df"].copy()
    enriched:  pd.DataFrame = st.session_state["enriched"].copy()

    st.subheader("Download your data")
    st.caption("Choose a format below to export tracks and (deduped) artists.")

    colA, colB, colC = st.columns([1.2, 1, 1.2])
    with colA:
        fmt = st.radio("Format", ["CSV", "Parquet"], horizontal=True, index=0)
    with colB:
        genre_format = st.selectbox("Genre field format", ["json", "pipe"], index=0, help="How to serialize the genres list")
    with colC:
        include_index = st.checkbox("Include index (CSV only)", value=False)

    # ---- Tracks export ----
    st.markdown("**Tracks**")
    tracks_out = tracks_df.copy()
    # Keep a sensible subset/order; export everything if you prefer
    cols = ["id", "name", "artist", "album", "release_year", "popularity", "url", "image", "added_at", "added_by_name"]
    tracks_out = tracks_out[[c for c in cols if c in tracks_out.columns]]

    if fmt == "CSV":
        csv_bytes = tracks_out.to_csv(index=include_index).encode("utf-8")
        st.download_button(
            "Download Tracks (CSV)",
            csv_bytes,
            file_name="playlist_tracks.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        # Parquet to an in-memory buffer
        buf = io.BytesIO()
        tracks_out.to_parquet(buf, index=False)
        st.download_button(
            "Download Tracks (Parquet)",
            buf.getvalue(),
            file_name="playlist_tracks.parquet",
            mime="application/octet-stream",
            use_container_width=True,
        )

    st.divider()

    # ---- Artists export (deduped) ----
    st.markdown("**Artists (deduped)**")
    if {"artist_id", "artist_name"}.issubset(enriched.columns):
        export_art = (
            enriched[["artist_id", "artist_name", "genres", "artist_popularity"]]
            .drop_duplicates(subset=["artist_id"])
            .reset_index(drop=True)
        )
        if "genres" in export_art.columns:
            export_art["genres"] = _serialize_genres(export_art["genres"], mode=genre_format)

        if fmt == "CSV":
            csv_bytes = export_art.to_csv(index=include_index).encode("utf-8")
            st.download_button(
                "Download Artists (CSV)",
                csv_bytes,
                file_name="artists.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            buf = io.BytesIO()
            export_art.to_parquet(buf, index=False)
            st.download_button(
                "Download Artists (Parquet)",
                buf.getvalue(),
                file_name="artists.parquet",
                mime="application/octet-stream",
                use_container_width=True,
            )
    else:
        st.info("No artist details available to export.")
