# src/ui/typing.py
import time
import streamlit as st

def typewriter(container, text: str, chunk: int = 3, delay: float = 0.03, caret_color="#43a047"):
    """
    Animate text typing with a continuously blinking caret
    """
    if not text:
        return

    caret_html = f"""
    <style>
    @keyframes blink {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0; }}
        100% {{ opacity: 1; }}
    }}
    .caret {{
        display: inline-block;
        color: {caret_color};
        animation: blink 1s step-start infinite;
        margin-left: 2px;
    }}
    </style>
    """

    # Write the caret style once
    st.markdown(caret_html, unsafe_allow_html=True)

    # Animate typing
    for i in range(0, len(text), chunk):
        chunked = text[: i + chunk]
        container.markdown(
            f"{chunked}<span class='caret'>▌</span>",
            unsafe_allow_html=True,
        )
        time.sleep(delay)

    # Show final text with a blinking caret for 3 seconds, then remove
    container.markdown(f"{text}<span class='caret'>▌</span>", unsafe_allow_html=True)
    time.sleep(3)
    container.markdown(text, unsafe_allow_html=True)
