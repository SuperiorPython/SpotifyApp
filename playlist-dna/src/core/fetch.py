# src/core/fetch.py
import re
import time
import pandas as pd
import streamlit as st
from src.core.auth import spotify_call, build_spotify_client


ID_RE = re.compile(r"^[A-Za-z0-9]{22}$")

sp = build_spotify_client()

def extract_playlist_id(s: str):
    if not s:
        return None
    s = s.strip()
    m = re.match(r"^spotify:playlist:([A-Za-z0-9]{22})$", s)
    if m:
        return m.group(1)
    m = re.search(r"playlist/([A-Za-z0-9]{22})", s)
    if m:
        return m.group(1)
    if ID_RE.match(s):
        return s
    return None


@st.cache_data(show_spinner=False, ttl=600)
def get_playlist_meta(_sp, playlist_id: str, market: str = "US"):
    return spotify_call(_sp.playlist, playlist_id, market=market)



@st.cache_data(show_spinner=False, ttl=600)
def fetch_playlist_tracks(_sp, playlist_id: str, market: str = "US"):
    results = spotify_call(_sp.playlist_tracks, playlist_id, market=market)
    items = results.get("items", [])
    while results.get("next"):
        results = sp.next(results)
        items += results.get("items", [])

    rows, dropped = [], 0
    for it in items:
        tr = (it or {}).get("track") or {}
        if tr.get("type") != "track" or tr.get("is_local") or not tr.get("id"):
            dropped += 1
            continue

        release = (tr.get("album") or {}).get("release_date") or ""
        year = int(release[:4]) if release[:4].isdigit() else None

        rows.append({
            "id": tr["id"],
            "name": tr.get("name", "—"),
            "artist": ", ".join(a.get("name", "") for a in tr.get("artists", [])) or "—",
            "artist_ids": [a.get("id") for a in tr.get("artists", []) if a.get("id")],
            "album": (tr.get("album") or {}).get("name", "—"),
            "release_year": year,
            "popularity": tr.get("popularity", 0),
            "url": (tr.get("external_urls") or {}).get("spotify"),
            "image": ((tr.get("album") or {}).get("images") or [{}])[0].get("url"),
            "added_at": it.get("added_at"),
            "added_by": (it.get("added_by") or {}).get("id") or "unknown",
            "added_by_name": (
                (it.get("added_by") or {}).get("display_name")
                or (it.get("added_by") or {}).get("id")
                or "unknown"
            ),
        })

    df = pd.DataFrame(rows).drop_duplicates(subset=["id"]).reset_index(drop=True)
    return df, dropped


@st.cache_data(show_spinner=False, ttl=600)
def fetch_artists_details(_sp, artist_ids: list[str]) -> pd.DataFrame:
    artist_ids = list(dict.fromkeys([a for a in artist_ids if a]))
    artists = []
    for i in range(0, len(artist_ids), 50):
        chunk = artist_ids[i:i + 50]
        res = sp.artists(chunk)
        artists.extend(res.get("artists", []))
        time.sleep(0.05)

    rows = []
    for a in artists:
        rows.append({
            "artist_id": a.get("id"),
            "artist_name": a.get("name"),
            "genres": a.get("genres", []),
            "artist_popularity": a.get("popularity", 0),
        })

    return pd.DataFrame(rows)
