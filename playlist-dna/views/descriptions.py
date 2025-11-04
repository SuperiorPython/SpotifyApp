# src/views/description.py
import os
import streamlit as st
import pandas as pd
import altair as alt

def render_description():
    st.title("About • Playlist DNA")

    st.markdown(
        """
Playlist DNA analyzes **any public Spotify playlist** and turns it into clear visuals and a short, human-readable vibe summary.

### What you can do
- **Overview** – key stats, a sample of tracks, and a genre donut  
- **Evolution** – growth over time, genre share by month, and weekday×hour activity  
- **Genres & Artists** – top genres and lead artists with interactive filters  
- **Time** – decade distribution and artist×year heatmap  
- **Popularity** – histogram and popularity vs. release year scatter  
- **Covers** – tidy album-art grid  
- **AI Companion** – ~160–220 word vibe summary (optional OpenAI key)  
- **Export** – download playlist tracks and artist details as CSV
"""
    )

    st.markdown("### How it works")
    st.markdown(
        """
- Uses **Spotify Web API** via **client credentials** (no user login required).
- Fetches playlist metadata, tracks, and artists; enriches artists with **genres** and popularity.
- **Altair** and **Pandas** power the charts; **Streamlit** powers the UI.
- If an **OpenAI key** is set, the AI summary blends genres, artist frequency, decade spread, popularity, and **evolution** stats.  
  The **playlist title** is used as a *soft hint* (it won’t override the data).
- If there’s no key or an API error, a **deterministic rule-based fallback** produces a concise summary.
"""
    )

    st.markdown("### Privacy & data")
    st.markdown(
        """
- Only works with **public playlists**. No access to private data.  
- Data is fetched from Spotify’s public endpoints at view time; nothing is stored server-side.  
- Track availability, images, and genres may vary by region.  
- **Audio features** are not used due to access limitations in third-party contexts.
"""
    )

    st.markdown("### Known limitations & bugs")
    st.markdown(
        """
- **One-time “tab bounce”**: The first interaction with a button/slider **inside any tab** may reroute you to **Overview** once per session.  
  *Workaround*: click back into your tab; it won’t recur for that session.
- **Public playlists made by Spotify accounts only**: Personalized lists (e.g., Discover Weekly) aren’t available via client-credentials.
- **Incomplete `added_at`**: Some playlists lack reliable “date added” data; **Evolution** visuals may be limited or absent.
- **Genre coverage**: Genre labels come from artists; niche artists may not have strong tagging → “unknown” or sparse distributions.
- **Region gating**: Tracks not available in your configured **Market** (e.g., US) are skipped → lower track counts.
- **AI variability**: AI summaries are probabilistic; tone is guided but may vary slightly across runs.
"""
    )

    st.markdown("### Tips & troubleshooting")
    st.markdown(
        """
- If charts look empty, try switching **Market** in Advanced (US/GB/DE/FR/CA/AU/BR/JP).  
- Use **Genres → Clear filter** if your selection becomes too narrow.  
- If the app gets into a weird state, use **sidebar → Clear cache & rerun**.
- For best results, start with playlists that have **≥ 30 tracks** and a mix of artists.
"""
    )

    st.markdown("### Roadmap")
    st.markdown(
        """
- Playlist **evolution timelapse** and smoother first-interaction behavior  
- Cross-playlist compare view  
- Optional **user auth** (private playlists)  
- More AI insights (tone, context snippets) with clear opt-in
"""
    )

    st.markdown("### Credits")
    st.markdown(
        """
Built with **Streamlit**, **Altair**, **Pandas**, and **Spotipy** (Spotify Web API).  
AI summaries via **OpenAI** (optional).  
"""
    )

    with st.expander("Environment details"):
        st.write("Streamlit:", st.__version__)
        st.write("Altair:", alt.__version__)
        st.write("Pandas:", pd.__version__)
        st.write("OpenAI key configured:", bool(st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")))
