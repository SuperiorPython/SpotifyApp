# src/core/auth.py
import os
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException

CLIENT_ID = st.secrets.get("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = st.secrets.get("SPOTIFY_CLIENT_SECRET") or os.getenv("SPOTIFY_CLIENT_SECRET")

def build_spotify_client():
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error("Missing SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in Streamlit Secrets (or env).")
        st.stop()
    auth = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    token = auth.get_access_token()  # force   early failure if creds wrong
    if not token:
        st.error("Could not obtain a client-credentials token. Check your Client ID/Secret.")
        st.stop()
    st.caption(f"✅ Token acquired · client …{CLIENT_ID[-6:]}")
    return spotipy.Spotify(
        auth_manager=auth,
        requests_timeout=10,
        retries=3,
        status_forcelist=(429, 500, 502, 503, 504),
    )

sp = build_spotify_client()

def spotify_call(fn, *args, **kwargs):
    """Retry once on 401/403 by rebuilding the client (handles stale token)."""
    global sp
    try:
        return fn(*args, **kwargs)
    except SpotifyException as e:
        if getattr(e, "http_status", None) in (401, 403):
            sp = build_spotify_client()
            return fn(*args, **kwargs)
        raise
