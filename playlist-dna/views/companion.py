# src/views/ai_companion.py
import os
import streamlit as st

from src.core.stats import (
    compute_stats,
    compute_evolution_stats,
    pick_openai_model,
    llm_vibe_summary_detailed,
    build_rule_based_summary,
)

def render_companion(PALETTE, PRIMARY, SECONDARY, FILL):
    """AI tab: one-click detailed vibe with evolution-aware summary."""
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

    # Output placeholder (persists across reruns)
    out = st.empty()

    # Generate button
    if st.button("Generate detailed vibe", type="primary", use_container_width=True):
        stats     = compute_stats(tracks_df, enriched)
        evolution = compute_evolution_stats(tracks_df, enriched)

        with st.spinner("Crafting your playlist vibe…"):
            text, used_model = (None, None)
            if has_key:
                text, used_model = llm_vibe_summary_detailed(stats, evolution=evolution)

            # Fallback (no key or API error)
            if not text:
                text = build_rule_based_summary(stats, evolution=evolution)
                used_model = used_model or "local-fallback"

        st.session_state["vibe_text"]  = text
        st.session_state["vibe_model"] = used_model
        out.write(text)
        st.caption(f"Source: {used_model}")

    # Show previous result if user navigates away/back
    elif st.session_state.get("vibe_text"):
        out.write(st.session_state["vibe_text"])
        if st.session_state.get("vibe_model"):
            st.caption(f"Source: {st.session_state['vibe_model']}")
