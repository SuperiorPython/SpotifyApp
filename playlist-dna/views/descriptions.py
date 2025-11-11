# src/views/description.py
import os
import datetime
import streamlit as st
import pandas as pd
import altair as alt

def render_description():
    st.title("About • Playlist DNA")

    st.markdown(
        """
Playlist DNA transforms **any public Spotify playlist** into interactive visuals and a narrative-style **vibe summary** that captures its sound, energy, and evolution.  
It’s designed for music lovers, data explorers, and creators who want to *see the story behind their playlists*.
"""
    )

    st.markdown("### What you can explore")
    st.markdown(
        """
- **Overview** – key stats, track sample, and a genre donut  
- **Evolution** – playlist growth, genre shifts, and weekday×hour activity  
- **Genres & Artists** – explore top genres and lead artists interactively  
- **Time** – decade breakdown and artist×year heatmap  
- **Popularity** – histogram plus popularity vs. release year  
- **Covers** – clean album-art grid  
- **AI Companion** – 200–300 word *vibe essay* powered by OpenAI (optional)  
- **Search** – find a specific song to view its **popularity, genre tags, and date added**  
- **Export** – download playlist and artist data as CSV
"""
    )

    st.markdown("### How it works")
    st.markdown(
        """
- Uses **Spotify’s Web API** through the **client credentials** method (no login required).  
- Collects playlist metadata, track info, and artist genres with popularity scores.  
- **Altair** and **Pandas** handle the analytics; **Streamlit** powers the visual experience.  
- If you configure an **OpenAI key**, the AI Companion merges genre trends, artist frequencies, popularity, and evolution stats.  
  The **playlist title** acts as a stylistic cue — it shapes tone but never overrides data.  
- Without a key, a deterministic **rule-based summary** ensures consistent fallback text.
"""
    )

    st.markdown("### Privacy & data")
    st.markdown(
        """
- Only supports **public playlists** — no access to private Spotify data.  
- Data is fetched live from Spotify’s public endpoints; nothing is stored on servers.  
- Some tracks, genres, or images may differ by region.  
- **Audio features** (like tempo or danceability) are excluded due to API limitations.
"""
    )

    st.markdown("### Known limitations")
    st.markdown(
        """
- **One-time tab bounce** – First click inside any tab may briefly reroute to *Overview* once per session.  
  *(Workaround: click back into your tab — it won’t happen again.)*  
- **Spotify-made playlists only** – Personalized lists (like *Discover Weekly*) can’t be fetched via client credentials.  
- **Missing timestamps** – Some playlists lack `added_at` data; *Evolution* and *Search* visuals may show partial results.  
- **Genre sparsity** – Some niche artists lack proper tagging, showing “unknown.”  
- **Region gating** – Tracks unavailable in your selected **Market** are skipped.  
- **AI variability** – AI summaries are slightly different across sessions by design.
"""
    )

    st.markdown("### Tips & troubleshooting")
    st.markdown(
        """
- Empty charts? Try another **Market** (US, GB, DE, FR, CA, AU, BR, JP).  
- Overfiltered genres? Use **Clear filter** to reset.  
- Misalignment? Use **Clear cache & rerun** from the sidebar.  
- For better summaries, use playlists with **30+ diverse tracks**.
"""
    )

    st.markdown("### Roadmap")
    st.markdown(
        """
- Playlist **evolution timelapse** visualization  
- Cross-playlist comparison  
- Optional **Spotify login** for private lists  
- Richer AI Companion insights (tone, emotional palette, trends)  
- Improved *Search* tab with artist-link previews
"""
    )

    st.markdown("### Credits")
    st.markdown(
        """
Built with **Streamlit**, **Altair**, **Pandas**, and **Spotipy**.  
AI Companion powered by **OpenAI** (optional).  
"""
    )

    with st.expander("Environment details"):
        st.write("Streamlit:", st.__version__)
        st.write("Altair:", alt.__version__)
        st.write("Pandas:", pd.__version__)
        st.write("OpenAI key configured:", bool(st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")))

    # --- Footer ---
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align:center; font-size:0.9em; color:gray;'>
            <b>Playlist DNA</b> • v1.3 — Updated {datetime.date.today().strftime('%B %Y')}  
            Built for discovery, powered by data 🎧
        </div>
        """,
        unsafe_allow_html=True
    )
