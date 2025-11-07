# src/ui/typing.py
import time
import streamlit as st

def typewriter(container, text: str, chunk: int = 4, delay: float = 0.015, caret: str = "▌"):
    """Animate text into the given container."""
    if not text:
        return
    # optional: reduce reflow by pre-allocating lines (not strictly necessary)
    for i in range(0, len(text), chunk):
        container.markdown(text[: i + chunk] + f"<span style='opacity:0.6'>{caret}</span>", unsafe_allow_html=True)
        time.sleep(delay)
    container.markdown(text, unsafe_allow_html=True)
