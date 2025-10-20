import streamlit as st
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import numpy as np

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Spotify Playlist Recommender", page_icon="🎧", layout="wide")

# Spotify Auth (Client Credentials flow)
CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

# ----------------------------
# FUNCTIONS
# ----------------------------
def extract_playlist_id(url_or_uri):
    """Extract playlist ID from URL or Spotify URI"""
    if "playlist/" in url_or_uri:
        return url_or_uri.split("playlist/")[1].split("?")[0]
    elif "spotify:playlist:" in url_or_uri:
        return url_or_uri.split(":")[-1]
    return url_or_uri.strip()

def fetch_playlist_tracks(playlist_id):
    """Fetch all tracks from a public playlist"""
    results = sp.playlist_tracks(playlist_id)
    tracks = results["items"]
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])
    track_data = []
    for item in tracks:
        track = item["track"]
        if track:
            track_data.append({
                "id": track["id"],
                "name": track["name"],
                "artist": ", ".join([a["name"] for a in track["artists"]]),
                "album": track["album"]["name"],
                "url": track["external_urls"]["spotify"],
                "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
            })
    return pd.DataFrame(track_data)

def get_audio_features(track_ids):
    """Get Spotify audio features for a list of track IDs"""
    feats = []
    for i in range(0, len(track_ids), 50):
        chunk = track_ids[i:i+50]
        feats.extend(sp.audio_features(chunk))
    return pd.DataFrame(feats)

def compute_vibe_centroid(df_features):
    """Compute mean of key audio features"""
    numeric_cols = ["danceability","energy","valence","acousticness","instrumentalness","liveness","speechiness","tempo"]
    return df_features[numeric_cols].mean().to_dict()

def recommend_from_centroid(centroid, seed_artists=None, seed_tracks=None, limit=10):
    """Call Spotify recommendations API using centroid as target features"""
    seeds = {
        "seed_tracks": seed_tracks[:2] if seed_tracks else None,
        "seed_artists": seed_artists[:2] if seed_artists else None,
        "limit": limit,
        "target_danceability": centroid["danceability"],
        "target_energy": centroid["energy"],
        "target_valence": centroid["valence"],
        "target_tempo": centroid["tempo"],
    }
    return sp.recommendations(**{k:v for k,v in seeds.items() if v})

# ----------------------------
# UI
# ----------------------------
st.title("🎧 Spotify Playlist Recommender")
st.caption("Paste a **public Spotify playlist link**, and get similar track recommendations.")

playlist_url = st.text_input("Enter public playlist URL or Spotify URI", placeholder="https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")

if st.button("Analyze Playlist"):
    try:
        playlist_id = extract_playlist_id(playlist_url)
        st.info("Fetching playlist tracks...")
        tracks_df = fetch_playlist_tracks(playlist_id)
        st.success(f"Fetched {len(tracks_df)} tracks!")

        track_ids = tracks_df["id"].dropna().tolist()
        features_df = get_audio_features(track_ids)

        # merge & analyze
        full_df = tracks_df.merge(features_df, left_on="id", right_on="id")
        centroid = compute_vibe_centroid(full_df)

        st.subheader("Playlist Summary")
        st.write(pd.DataFrame([centroid]).T.rename(columns={0:"avg_value"}))

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Energy", f"{centroid['energy']:.2f}")
        col2.metric("Avg Danceability", f"{centroid['danceability']:.2f}")
        col3.metric("Avg Valence (Happiness)", f"{centroid['valence']:.2f}")

        st.info("Generating similar track recommendations...")
        recs = recommend_from_centroid(centroid, seed_tracks=track_ids[:3])
        recs_df = pd.DataFrame([{
            "name": t["name"],
            "artist": ", ".join([a["name"] for a in t["artists"]]),
            "url": t["external_urls"]["spotify"],
            "image": t["album"]["images"][0]["url"] if t["album"]["images"] else None
        } for t in recs["tracks"]])

        st.subheader("🎵 Recommended Songs")
        cols = st.columns(2)
        for i, row in recs_df.iterrows():
            with cols[i % 2]:
                if row["image"]:
                    st.image(row["image"], width=80)
                st.markdown(f"**[{row['name']}]({row['url']})** — {row['artist']}")

    except Exception as e:
        st.error(f"Error: {e}")
