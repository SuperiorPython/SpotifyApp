# views/companion.py
import os
from pathlib import Path
import streamlit as st
from src.core.stats import compute_stats, compute_evolution_stats, pick_openai_model, llm_vibe_summary_detailed, build_rule_based_summary
from src.ui.typing import typewriter

APP_DIR = Path(__file__).resolve().parents[1]
ROBOT_PATH = APP_DIR / "assets" / "robot_image.png"   # <-- place your image here

def render_companion(PALETTE, PRIMARY, SECONDARY, FILL):
    if "tracks_df" not in st.session_state or "enriched" not in st.session_state:
        st.info("Analyze a playlist to view the AI companion.")
        return

    tracks_df = st.session_state["tracks_df"]
    enriched  = st.session_state["enriched"]

    st.subheader("Playlist Companion (AI)")

    has_key = bool(st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
    model_note = pick_openai_model() if has_key else None
    st.markdown(
        f"✨ **AI mode** — {model_note or 'auto'}"
        if has_key else
        "⚙️ **Local mode (free)** — AI key not configured"
    )

    # --- Layout: text left, robot right
    text_col, robot_col = st.columns([3, 1], vertical_alignment="top")

    # Robot styles (glow + gentle float). Mirror X if your PNG faces right.
    with robot_col:
        st.markdown(
            """
            <style>
              .robot-wrap img{
                width:100%;
                filter: drop-shadow(0 0 22px rgba(67,160,71,0.9));
                /* flip horizontally if your source faces right; comment out if already facing left */
                transform: scaleX(-1);
              }
              @keyframes floaty {
                0%   { transform: translateY(0)    scaleX(-1); }
                50%  { transform: translateY(-6px) scaleX(-1); }
                100% { transform: translateY(0)    scaleX(-1); }
              }
              .floaty { animation: floaty 3s ease-in-out infinite; }
            </style>
            """,
            unsafe_allow_html=True
        )

    # Placeholder for typed summary on the left
    out = text_col.empty()

    # Robot displayed whenever we’re generating or showing output
    def show_robot():
        if ROBOT_PATH.exists():
            with robot_col:
                st.markdown("<div class='robot-wrap floaty'>", unsafe_allow_html=True)
                st.image(str(ROBOT_PATH), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

    # Controls
    c1, c2 = text_col.columns([1,1])
    gen = c1.button("Generate detailed vibe", type="primary", use_container_width=True)
    regen = c2.button("Regenerate", type = "primary", use_container_width=True, key="regen_btn",
                      help="Try a fresh take")

    # Generate/Regenerate behavior
    if gen or regen:
        stats = compute_stats(tracks_df, enriched)
        evolution = compute_evolution_stats(tracks_df, enriched)
        title = st.session_state.get("meta", {}).get("name")

        # Show robot immediately as we start typing
        show_robot()

        with st.spinner("Crafting your playlist vibe…"):
            text, used_model = (None, None)
            if has_key:
                text, used_model = llm_vibe_summary_detailed(stats, evolution=evolution, playlist_title=title)
            if not text:
                text = build_rule_based_summary(stats, evolution=evolution, playlist_title=title)
                used_model = used_model or "local-fallback"

        # Save + animate
        st.session_state["vibe_text"] = text
        st.session_state["vibe_model"] = used_model
        # slower typing + green caret already handled in typewriter module
        typewriter(out, text, chunk=3, delay=0.04, caret_color="#43a047")
        text_col.caption(f"Source: {used_model}")

    elif st.session_state.get("vibe_text"):
        # If we already have a summary, show robot + pinned text
        show_robot()
        out.markdown(st.session_state["vibe_text"])
        if st.session_state.get("vibe_model"):
            text_col.caption(f"Source: {st.session_state['vibe_model']}")
