# src/core/stats.py
from __future__ import annotations

import os
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import streamlit as st


# ------------------------- Snapshot stats ------------------------- #

def compute_stats(tracks_df: pd.DataFrame, enriched: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute snapshot stats for the current playlist state.
    Returns:
        {
          "top_genres": List[(genre, pct_int)],
          "top_artists": List[(artist, count)],
          "decades": {decade_int: count},
          "median_pop": float
        }
    """
    # Top genres (percentage by occurrences in exploded genres)
    g = enriched.explode("genres")["genres"].dropna()
    top_genres_counts = g.value_counts()
    total = int(top_genres_counts.sum()) or 1
    top_genres_pct = [(k, int(round(v * 100 / total))) for k, v in top_genres_counts.items()]

    # Lead artists (by first listed artist)
    lead = enriched.copy()
    lead["lead_artist"] = lead["artist"].str.split(", ").str[0]
    top_artists = list(lead["lead_artist"].value_counts().head(10).items())

    # Decades
    td = tracks_df.dropna(subset=["release_year"]).copy()
    td["decade"] = (td["release_year"] // 10) * 10
    decades = td["decade"].value_counts().sort_index().to_dict()

    # Popularity (median)
    median_pop = float(tracks_df["popularity"].median()) if not tracks_df.empty else 0.0

    return {
        "top_genres": top_genres_pct,
        "top_artists": top_artists,
        "decades": decades,
        "median_pop": median_pop,
    }


# ----------------------- Evolution over time ---------------------- #

def compute_evolution_stats(tracks_df: pd.DataFrame, enriched: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Summarize how the playlist evolved using `added_at` timestamps.

    Returns None if no `added_at` data is available, else:
        {
          "total_tracks": int,
          "first_date": "YYYY-MM-DD",
          "last_date": "YYYY-MM-DD",
          "days_span": int,
          "adds_per_day": float,
          "bursts_top": List[(date_str, count_int)],
          "median_age_years": Optional[float],
          "rising_genres": List[(genre, +share_float)],
          "falling_genres": List[(genre, -share_float)]
        }
    """
    if "added_at" not in tracks_df or tracks_df["added_at"].isna().all():
        return None

    t = tracks_df.dropna(subset=["added_at"]).copy()
    # Normalize times to naive for grouping
    t["date"] = t["added_at"].dt.tz_convert(None).dt.date
    t["month"] = t["added_at"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()

    # Growth basics
    per_day = t.groupby("date").size().reset_index(name="added").sort_values("date")
    total_tracks = int(t["id"].nunique())
    first_date = per_day["date"].min()
    last_date = per_day["date"].max()
    days_span = (pd.to_datetime(last_date) - pd.to_datetime(first_date)).days or 1
    adds_per_day = float(per_day["added"].mean())

    # Bursts
    bursts = per_day.sort_values("added", ascending=False).head(3)
    bursts_summary = [(str(d), int(n)) for d, n in zip(bursts["date"], bursts["added"])]

    # Novelty: age (years) at add time
    td = t.dropna(subset=["release_year"]).copy()
    if not td.empty:
        td["added_year"] = td["added_at"].dt.tz_convert(None).dt.year
        td["age_years"] = td["added_year"] - td["release_year"]
        median_age = float(td["age_years"].median())
    else:
        median_age = None

    # Genre shift: early vs late month shares for top genres
    g = enriched.dropna(subset=["added_at"]).copy()
    g["month"] = g["added_at"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()
    g = g.explode("genres")
    g["genres"] = g["genres"].fillna("unknown")

    if g.empty:
        rising = []
        falling = []
    else:
        topK = g["genres"].value_counts().head(8).index.tolist()
        g = g[g["genres"].isin(topK)]
        early = g[g["month"] <= (g["month"].min() + pd.offsets.MonthEnd(1))]
        late = g[g["month"] >= (g["month"].max() - pd.offsets.MonthEnd(1))]

        def norm_share(df: pd.DataFrame) -> pd.Series:
            tmp = df.groupby("genres").size().reset_index(name="count")
            s = int(tmp["count"].sum()) or 1
            tmp["share"] = tmp["count"] / s
            return tmp.set_index("genres")["share"]

        early_s, late_s = norm_share(early), norm_share(late)
        all_g = sorted(set(early_s.index) | set(late_s.index))
        deltas: List[Tuple[str, float]] = []
        for gname in all_g:
            deltas.append((gname, float(late_s.get(gname, 0.0) - early_s.get(gname, 0.0))))
        deltas.sort(key=lambda x: x[1], reverse=True)

        rising = [(name, round(delta, 3)) for name, delta in deltas[:3] if delta > 0]
        falling = [(name, round(delta, 3)) for name, delta in deltas[-3:] if delta < 0]

    return {
        "total_tracks": total_tracks,
        "first_date": str(first_date),
        "last_date": str(last_date),
        "days_span": int(days_span),
        "adds_per_day": round(adds_per_day, 2),
        "bursts_top": bursts_summary,
        "median_age_years": median_age,
        "rising_genres": rising,
        "falling_genres": falling,
    }


# ----------------------- Rule-based fallback ---------------------- #

def build_rule_based_summary(stats, evolution=None, playlist_title: str | None = None):
    g = stats["top_genres"]; a = stats["top_artists"]; d = stats["decades"]; pop = stats["median_pop"]
    genre_line = ", ".join([f"{name} ({pct}%)" for name, pct in g[:3]]) if g else "a mix of styles"
    artist_line = ", ".join([name for name, _ in a[:3]]) if a else "various artists"
    if d:
        keys = list(d.keys()); first, last = keys[0], keys[-1]; tilt = max(d, key=d.get)
        era_line = f"spans {first}s–{last}s with a {tilt}s tilt"
    else:
        era_line = "spans multiple eras"
    mainstream = ("underground" if pop < 40 else "balanced" if pop < 65 else "mainstream-leaning")

    evo_line = ""
    if evolution:
        pace = "steady" if evolution["adds_per_day"] >= 0.3 else "occasional"
        if evolution["adds_per_day"] >= 1.0: pace = "bursty"
        novelty = ""
        if evolution.get("median_age_years") is not None:
            novelty = "recent-leaning" if evolution["median_age_years"] <= 3 else "nostalgic" if evolution["median_age_years"] >= 12 else "mixed-era"
        rise = (", rising: " + ", ".join(g for g,_ in evolution.get("rising_genres", [])[:2])) if evolution.get("rising_genres") else ""
        fall = (", cooling: " + ", ".join(g for g,_ in evolution.get("falling_genres", [])[:2])) if evolution.get("falling_genres") else ""
        evo_line = f" Curation pace feels {pace}{(', ' + novelty) if novelty else ''}{rise}{fall}."

    title_hint = ""
    if playlist_title:
        t = playlist_title.strip()
        if len(t) >= 3 and t.lower() not in {"my playlist","playlist","mix"}:
            title_hint = f" The title “{t}” hints at the intended vibe."

    return (
        f"This playlist feels {mainstream}. Dominant flavors: {genre_line}. "
        f"Frequent artists include {artist_line}. It {era_line}.{evo_line}{title_hint}"
    )


# ----------------------- LLM model selection ---------------------- #

@st.cache_resource
def pick_openai_model() -> Optional[str]:
    """
    Returns preferred available OpenAI model ID if API key is configured, else None.
    Checks for OPENAI_MODEL override first.
    """
    override = st.secrets.get("OPENAI_MODEL") or os.getenv("OPENAI_MODEL")
    if override:
        return override

    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        ids = {m.id for m in client.models.list().data}
        for m in ["gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5-turbo"]:
            if m in ids:
                return m
    except Exception:
        pass
    return None


# ---------------------------- LLM summary ---------------------------- #

def llm_vibe_summary_detailed(stats, evolution=None, vibe_hint=None, playlist_title: str | None = None):
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, None

    model = pick_openai_model() or "gpt-4"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        genres_str  = ", ".join([f"{g} {p}%" for g, p in stats["top_genres"][:8]]) or "n/a"
        artists_str = ", ".join([a for a, _ in stats["top_artists"][:12]]) or "n/a"
        decades_str = ", ".join([f"{k}s:{v}" for k, v in stats["decades"].items()]) or "n/a"
        median_pop  = int(stats["median_pop"])
        title_str   = (playlist_title or "").strip() or "none"

        evo_lines = []
        if evolution:
            evo_lines.append(f"- Observed window: {evolution['first_date']} → {evolution['last_date']} ({evolution['days_span']} days)")
            evo_lines.append(f"- Avg adds/day: {evolution['adds_per_day']}")
            if evolution.get("bursts_top"):
                burst_fmt = "; ".join([f"{d} (+{n})" for d, n in evolution["bursts_top"]])
                evo_lines.append(f"- Burst days: {burst_fmt}")
            if evolution.get("median_age_years") is not None:
                evo_lines.append(f"- Median track age at add: {round(evolution['median_age_years'],1)} years")
            if evolution.get("rising_genres"):
                evo_lines.append("- Rising genres: " + ", ".join([f"{g} (+{abs(s):.0%})" for g, s in evolution["rising_genres"]]))
            if evolution.get("falling_genres"):
                evo_lines.append("- Declining genres: " + ", ".join([f"{g} ({-abs(s):.0%})" for g, s in evolution["falling_genres"]]))
        evo_block = "\n".join(evo_lines) if evo_lines else "none"

        system = (
            "You are a thoughtful music curator. Write vivid, specific descriptions. "
            "Use the playlist title only as a weak hint of intent—do not let a cheeky title override the data."
        )
        user = (
            "Create a detailed vibe summary for a Spotify playlist using these stats.\n\n"
            f"PLAYLIST TITLE: {title_str}\n"
            f"CURRENT SNAPSHOT\n"
            f"- Top genres: {genres_str}\n"
            f"- Frequent artists: {artists_str}\n"
            f"- Decade distribution: {decades_str}\n"
            f"- Median popularity (0-100): {median_pop}\n"
            f"- Style hint (optional): {vibe_hint or 'none'}\n\n"
            f"EVOLUTION SNAPSHOT (if any)\n{evo_block}\n\n"
            "Write ~160–220 words. Include:\n"
            "1) Core mood & energy (what it feels like and why)\n"
            "2) Where/when it fits (study, commute, night drive, etc.)\n"
            "3) Sonic traits (rhythm/production/vocals/tempo)\n"
            "4) How the playlist evolved (pace of additions, rising/declining genres, novelty vs. nostalgia)\n"
            "Avoid long artist lists. No emojis."
        )

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            temperature=0.7,
            max_tokens=350,
        )
        text = resp.choices[0].message.content.strip()
        return text, model
    except Exception:
        return None, model

