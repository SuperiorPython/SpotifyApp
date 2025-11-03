# src/ui/cover.py
from pathlib import Path
import streamlit as st
from src.core.fetch import extract_playlist_id

def render_cover(cover_path: str = "assets/cover_image.png", size_px: int = 550):
    st.set_page_config(
        page_title="Playlist DNA",
        page_icon="🟢",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    """Centered, larger cover image and playlist URL input using pure Streamlit layout."""
    st.markdown(
        """
        <style>
            body {
                background-color: #000;
            }
            .title {
                color: #43a047; /* Spotify green */
                font-weight: 800;
                font-size: 42px;
                text-align: center;
                margin-top: 40px;
                margin-bottom: 10px;
                letter-spacing: 1px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="title">Playlist DNA</div>', unsafe_allow_html=True)

    # --- Center image using wider middle column ---
    left, mid, right = st.columns([7, 7, 7])  # wider middle column = larger centered image
    with mid:
        if Path(cover_path).exists():
            st.image(
                cover_path,
                width=size_px,
                caption=None,
                use_container_width=False
            )
        else:
            st.error(f"❌ Image not found: {cover_path}")

    st.write("")  # spacing below image

    with st.sidebar:
            if st.button("🔄 Clear cache & rerun", use_container_width=True):
                st.cache_data.clear()
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()

    c1, c2 = st.columns([3, 1])
    with c1:
        playlist_url = st.text_input(
            "Playlist URL or URI",
            placeholder="https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            key="playlist_url"
        )
        if st.button("Analyze Playlist", type="primary", key="controls_analyze"):
            if extract_playlist_id(playlist_url):
                st.session_state["cover_playlist_url"] = playlist_url
                st.session_state["trigger_analyze"] = True
                st.rerun()
            else:
                st.warning("Please paste a valid link/URI/ID.")
    with c2:
        market = st.selectbox("Market", ["US", "GB", "DE", "FR", "CA", "AU", "BR", "JP"], index=0, key="market")

    with st.expander("Need a known-good test link?"):
        st.code("https://open.spotify.com/playlist/6sLKqrUF3TEfcMkcS6P3gu?si=a3a15e2943494449")