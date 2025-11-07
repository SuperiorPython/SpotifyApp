# views/companion.py
import os
import streamlit as st
from src.core.stats import (
    compute_stats,
    compute_evolution_stats,
    pick_openai_model,
    llm_vibe_summary_detailed,
    build_rule_based_summary,
)
from src.ui.typing import typewriter


def render_companion(PALETTE, PRIMARY, SECONDARY, FILL):
    if "tracks_df" not in st.session_state or "enriched" not in st.session_state:
        st.info("Analyze a playlist to view the AI companion.")
        return

    tracks_df = st.session_state["tracks_df"]
    enriched = st.session_state["enriched"]

    st.subheader("Playlist Companion (AI)")
    has_key = bool(st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
    model_note = pick_openai_model() if has_key else None
    st.markdown(
        f"✨ **AI mode** — {model_note or 'auto'}"
        if has_key
        else "⚙️ **Local mode (free)** — AI key not configured"
    )

    # Output container for animated text
    out = st.empty()

    # Button layout
    colA, colB = st.columns([1, 1])
    with colA:
        do_generate = st.button("Generate detailed vibe", type="primary", use_container_width=True)
    with colB:
        do_regen = st.button("Regenerate", type="primary", use_container_width=True)

    # Generate logic
    if do_generate or do_regen:
        stats = compute_stats(tracks_df, enriched)
        evolution = compute_evolution_stats(tracks_df, enriched)

        with st.spinner("Crafting your playlist vibe…"):
            text, used_model = (None, None)
            if has_key:
                text, used_model = llm_vibe_summary_detailed(stats, evolution=evolution)
            if not text:
                text = build_rule_based_summary(stats, evolution=evolution)
                used_model = used_model or "local-fallback"

        # Store + flag for animation
        st.session_state["vibe_text"] = text
        st.session_state["vibe_model"] = used_model
        st.session_state["vibe_should_animate"] = True

    # Display (animate only on new generation)
    if st.session_state.get("vibe_text"):
        if st.session_state.pop("vibe_should_animate", False):
            typewriter(out, st.session_state["vibe_text"], chunk=1, delay=0.05)  # ⏳ slower, smoother
        else:
            out.markdown(st.session_state["vibe_text"], unsafe_allow_html=True)

        if st.session_state.get("vibe_model"):
            st.caption(f"Source: {st.session_state['vibe_model']}")
