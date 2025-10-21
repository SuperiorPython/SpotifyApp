# app.py — Playlist Visual Footprint (stable tabs, persisted filters, LLM vibe optional)
import os, re, time
import streamlit as st
import pandas as pd
import altair as alt
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException

# ----------------- App setup -----------------
st.set_page_config(page_title="Playlist Visual Footprint", page_icon="🟢", layout="wide")
st.title("🟢 Playlist Visual Footprint")
st.caption("Analyze any **public** Spotify playlist. Green visuals • Stable tabs • Optional AI vibe summary.")

with st.sidebar:
    if st.button("🔄 Clear cache & rerun"):
        st.cache_data.clear()
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ---- Green brand palette ----
PALETTE = [
    "#1b5e20", "#2e7d32", "#388e3c", "#43a047", "#4caf50",
    "#66bb6a", "#81c784", "#a5d6a7", "#c8e6c9"
]
PRIMARY   = "#43a047"   # bars
SECONDARY = "#2e7d32"   # points/accents
FILL      = "#66bb6a"   # areas

# ----------------- Auth -----------------
CLIENT_ID = st.secrets.get("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = st.secrets.get("SPOTIFY_CLIENT_SECRET") or os.getenv("SPOTIFY_CLIENT_SECRET")

def build_spotify_client():
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error("Missing SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in Streamlit Secrets (or env).")
        st.stop()
    auth = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    token = auth.get_access_token()  # force early failure if creds wrong
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

# ----------------- Helpers -----------------
def extract_playlist_id(url_or_uri: str) -> str | None:
    if not url_or_uri: return None
    s = url_or_uri.strip()
    m = re.match(r"^spotify:playlist:([A-Za-z0-9]{22})$", s)
    if m: return m.group(1)
    m = re.search(r"playlist/([A-Za-z0-9]{22})", s)  # handles /intl-xx/ too
    if m: return m.group(1)
    if re.match(r"^[A-Za-z0-9]{22}$", s):  # raw id
        return s
    return None

@st.cache_data(show_spinner=False, ttl=600)
def get_playlist_meta(playlist_id: str, market: str = "US"):
    return spotify_call(sp.playlist, playlist_id, market=market)

@st.cache_data(show_spinner=False, ttl=600)
def fetch_playlist_tracks(playlist_id: str, market: str = "US"):
    """
    Return (tracks_df, dropped_count). Skips episodes/local/unavailable tracks.
    Columns: id, name, artist, artist_ids, album, release_year, popularity, url, image
    """
    results = spotify_call(sp.playlist_tracks, playlist_id, market=market)
    items = results.get("items", [])
    while results.get("next"):
        results = spotify_call(sp.next, results)
        items += results.get("items", [])

    rows, dropped = [], 0
    for it in items:
        tr = (it or {}).get("track") or {}
        if tr.get("type") != "track" or tr.get("is_local") or not tr.get("id"):
            dropped += 1
            continue
        release = (tr.get("album") or {}).get("release_date") or ""
        year = int(release[:4]) if release[:4].isdigit() else None
        rows.append({
            "id": tr["id"],
            "name": tr.get("name", "—"),
            "artist": ", ".join(a.get("name","") for a in tr.get("artists", [])) or "—",
            "artist_ids": [a.get("id") for a in tr.get("artists", []) if a.get("id")],
            "album": (tr.get("album") or {}).get("name", "—"),
            "release_year": year,
            "popularity": tr.get("popularity", 0),
            "url": (tr.get("external_urls") or {}).get("spotify"),
            "image": ((tr.get("album") or {}).get("images") or [{}])[0].get("url"),
        })
    df = pd.DataFrame(rows).drop_duplicates(subset=["id"]).reset_index(drop=True)
    return df, dropped

@st.cache_data(show_spinner=False, ttl=600)
def fetch_artists_details(artist_ids: list[str]) -> pd.DataFrame:
    """Batch /v1/artists (50 max per call). Returns df[artist_id, artist_name, genres, artist_popularity]."""
    artist_ids = list(dict.fromkeys([a for a in artist_ids if a]))
    artists = []
    for i in range(0, len(artist_ids), 50):
        chunk = artist_ids[i:i+50]
        res = spotify_call(sp.artists, chunk)
        artists.extend(res.get("artists", []))
        time.sleep(0.05)
    rows = []
    for a in artists:
        rows.append({
            "artist_id": a.get("id"),
            "artist_name": a.get("name"),
            "genres": a.get("genres", []),
            "artist_popularity": a.get("popularity", 0),
        })
    return pd.DataFrame(rows)

# ---------- Stats + AI helpers ----------
def compute_stats(tracks_df: pd.DataFrame, enriched: pd.DataFrame):
    # genres (percentage)
    g = enriched.explode("genres")["genres"].dropna()
    top_genres_counts = g.value_counts()
    total = int(top_genres_counts.sum()) or 1
    top_genres_pct = [(k, round(v * 100 / total)) for k, v in top_genres_counts.items()]

    # lead artists
    lead = enriched.copy()
    lead["lead_artist"] = lead["artist"].str.split(", ").str[0]
    top_artists = list(lead["lead_artist"].value_counts().head(10).items())

    # decades
    td = tracks_df.dropna(subset=["release_year"]).copy()
    td["decade"] = (td["release_year"] // 10) * 10
    decades = td["decade"].value_counts().sort_index().to_dict()

    # popularity
    median_pop = float(tracks_df["popularity"].median()) if not tracks_df.empty else 0.0

    return {
        "top_genres": top_genres_pct,    # list[(genre, pct)]
        "top_artists": top_artists,      # list[(artist, count)]
        "decades": decades,              # {decade: count}
        "median_pop": median_pop
    }

def build_rule_based_summary(stats):
    g = stats["top_genres"]; a = stats["top_artists"]; d = stats["decades"]; pop = stats["median_pop"]
    genre_line = ", ".join([f"{name} ({pct}%)" for name, pct in g[:3]]) if g else "a mix of styles"
    artist_line = ", ".join([name for name, _ in a[:3]]) if a else "various artists"
    if d:
        keys = list(d.keys())
        first, last = keys[0], keys[-1]
        tilt = max(d, key=d.get)
        era_line = f"spans {first}s–{last}s with a {tilt}s tilt"
    else:
        era_line = "spans multiple eras"
    mainstream = ("underground" if pop < 40 else "balanced" if pop < 65 else "mainstream-leaning")
    return (
        f"This playlist feels {mainstream}. Dominant flavors: {genre_line}. "
        f"Frequent artists include {artist_line}. It {era_line}. Expect a consistent vibe with a few left-field moments."
    )

def llm_vibe_summary(stats, vibe_hint=None):
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None  # no LLM; caller will fall back
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        genres_str = ", ".join([f"{g} {p}%" for g, p in stats["top_genres"][:6]]) or "n/a"
        artists_str = ", ".join([a for a, _ in stats["top_artists"][:10]]) or "n/a"
        decades_str = ", ".join([f"{k}s:{v}" for k, v in stats["decades"].items()]) or "n/a"
        median_pop = int(stats["median_pop"])

        system = (
            "You are a warm, vivid music curator. Write a compact vibe description (90–130 words). "
            "Focus on mood, energy, and scenes where this playlist fits. Avoid generic filler."
        )
        user = (
            f"Summarize the vibe of a Spotify playlist.\n\n"
            f"Top genres: {genres_str}\n"
            f"Frequent artists: {artists_str}\n"
            f"Decades spread: {decades_str}\n"
            f"Median popularity: {median_pop}\n"
            f"Style hint (optional): {vibe_hint or 'none'}\n"
            f"Please be specific, lively, and avoid listing too many names; emphasize feeling."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.75,
            max_tokens=220,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None

# ----------------- Controls -----------------
c1, c2 = st.columns([3,1])
with c1:
    playlist_url = st.text_input(
        "Playlist URL or URI",
        placeholder="https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        key="playlist_url"
    )
with c2:
    market = st.selectbox("Market", ["US","GB","DE","FR","CA","AU","BR","JP"], index=0, key="market")

with st.expander("Need a known-good test link?"):
    st.code("https://open.spotify.com/playlist/6sLKqrUF3TEfcMkcS6P3gu?si=a3a15e2943494449")

# Initialize persistent UI state
if "genre_filter" not in st.session_state:
    st.session_state["genre_filter"] = []
if "last_pid" not in st.session_state:
    st.session_state["last_pid"] = None

# ----------------- Analyze action (fetch + cache in session_state) -----------------
if st.button("Analyze Playlist", type="primary"):
    pid = extract_playlist_id(st.session_state["playlist_url"])
    if not pid:
        st.error("Please paste a valid **public** playlist link/URI (or a 22-char ID).")
        st.stop()

    with st.status("Analyzing playlist…", state="running") as status:
        try:
            status.update(label="Fetching metadata…")
            meta = get_playlist_meta(pid, market=st.session_state["market"])
            owner = (meta.get("owner") or {}).get("display_name", "unknown")
            pname = meta.get("name", "(no name)")

            status.update(label="Fetching tracks…")
            tracks_df, dropped = fetch_playlist_tracks(pid, market=st.session_state["market"])
            if tracks_df.empty:
                st.error("No usable tracks (playlist may be episodes/local/region-blocked). Try another.")
                st.stop()

            status.update(label="Enriching artists/genres…")
            all_artist_ids = [aid for lst in tracks_df["artist_ids"].dropna().tolist() for aid in (lst or [])]
            artists_df = fetch_artists_details(all_artist_ids)

            enriched = tracks_df.explode("artist_ids").rename(columns={"artist_ids":"artist_id"})
            if not artists_df.empty:
                enriched = enriched.merge(artists_df, on="artist_id", how="left")
            else:
                enriched["artist_name"] = enriched["artist"].str.split(", ").str[0]
                enriched["genres"] = [[] for _ in range(len(enriched))]
                enriched["artist_popularity"] = None

            # Persist results & randomized order once per playlist
            st.session_state["last_pid"] = pid
            st.session_state["meta"] = {"name": pname, "owner": owner, "dropped": dropped}
            st.session_state["tracks_df"] = tracks_df
            st.session_state["enriched"] = enriched

            # stable random indices for preview & covers per analyze
            seed = int(time.time())
            st.session_state["preview_idx"] = tracks_df.sample(frac=1, random_state=seed).index.tolist()
            st.session_state["covers_idx"]  = tracks_df.dropna(subset=["image"]).sample(frac=1, random_state=seed).index.tolist()

            status.update(label="Done ✅", state="complete")
        except SpotifyException as e:
            if getattr(e, "http_status", None) == 404:
                st.error("Playlist not found or not publicly accessible with client-credentials.")
            else:
                st.error(f"Spotify API error ({getattr(e,'http_status','n/a')}): {e}")
            st.stop()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

# ----------------- Stable tabs (always same order) -----------------
TABS = ["Overview","Genres","Artists","Time","Popularity","Covers","Companion (AI)","Export"]
tab_over, tab_gen, tab_art, tab_time, tab_pop, tab_cov, tab_ai, tab_export = st.tabs(TABS)

def need_analysis():
    return "tracks_df" not in st.session_state or "enriched" not in st.session_state

# ---- Overview tab ----
with tab_over:
    if need_analysis():
        st.info("Paste a public playlist and click **Analyze Playlist** to begin.")
    else:
        meta = st.session_state["meta"]
        tracks_df = st.session_state["tracks_df"]
        enriched = st.session_state["enriched"]

        st.caption(f"📃 Playlist: **{meta['name']}** by **{meta['owner']}**  •  Usable tracks: {len(tracks_df)}  •  Dropped: {meta['dropped']}")

        cA, cB, cC = st.columns(3)
        cA.metric("Tracks analyzed", tracks_df["id"].nunique())
        unique_artists = enriched.get("artist_name", pd.Series(dtype=str)).nunique() or tracks_df["artist"].nunique()
        cB.metric("Unique artists", int(unique_artists))
        cC.metric("Median popularity", int(tracks_df["popularity"].median() if not tracks_df.empty else 0))

        # Random sample (stable per analyze)
        N_PREVIEW = 15
        idxs = st.session_state.get("preview_idx", list(tracks_df.index))
        preview_df = tracks_df.loc[idxs[:min(N_PREVIEW, len(idxs))]]
        with st.expander(f"Show random sample ({len(preview_df)})"):
            st.dataframe(
                preview_df[["name","artist","album","release_year","popularity"]],
                use_container_width=True, hide_index=True
            )

        # Donut: top genres (big, tooltips only)
        g_exploded = enriched.explode("genres")
        genre_counts = g_exploded["genres"].dropna().value_counts().head(12).reset_index()
        genre_counts.columns = ["genre", "count"]

        st.subheader("Genre footprint (top 12)")
        if not genre_counts.empty:
            WIDTH, HEIGHT = 520, 520
            innerR, outerR = 120, 220
            donut = (
                alt.Chart(genre_counts)
                .encode(
                    theta=alt.Theta("count:Q", stack=True),
                    color=alt.Color("genre:N", legend=None, scale=alt.Scale(range=PALETTE)),
                    order=alt.Order("count:Q", sort="descending"),
                    tooltip=[alt.Tooltip("genre:N"), alt.Tooltip("count:Q")]
                )
                .mark_arc(innerRadius=innerR, outerRadius=outerR, stroke="white", strokeWidth=1)
                .properties(width=WIDTH, height=HEIGHT)
            )
            st.altair_chart(donut, use_container_width=True)
        else:
            st.info("No genre data available for a donut chart.")

# ---- Genres tab ----
with tab_gen:
    if need_analysis():
        st.info("Analyze a playlist to view Genres.")
    else:
        tracks_df = st.session_state["tracks_df"]
        enriched = st.session_state["enriched"]

        all_genres = (
            enriched.explode("genres")["genres"].dropna().value_counts().head(50).index.tolist()
        )
        sel_genres = st.multiselect(
            "Filter by genre (optional)",
            options=all_genres,
            default=st.session_state["genre_filter"],
            key="genre_filter"  # persists across reruns
        )

        filtered = (
            enriched[enriched["genres"].apply(lambda g: any(x in (g or []) for x in sel_genres))]
            if sel_genres else enriched
        )
        st.caption(f"Filtered tracks: {filtered['id'].nunique()} / {tracks_df['id'].nunique()}")

        fg = filtered.explode("genres")
        top_genres = (fg["genres"].dropna().value_counts().head(20).reset_index())
        top_genres.columns = ["genre","count"]

        if not top_genres.empty:
            chart_genres = alt.Chart(top_genres).mark_bar(color=PRIMARY).encode(
                x=alt.X("count:Q", title="Tracks"),
                y=alt.Y("genre:N", sort='-x', title=None),
                tooltip=["genre","count"]
            ).properties(height=420)
            st.altair_chart(chart_genres, use_container_width=True)
        else:
            st.info("No genre data available for these artists.")

# ---- Artists tab (lollipop chart, version-safe) ----
with tab_art:
    if need_analysis():
        st.info("Analyze a playlist to view Artists.")
    else:
        enriched = st.session_state["enriched"]
        lead = enriched.copy()
        lead["lead_artist"] = lead["artist"].str.split(", ").str[0]
        counts = lead["lead_artist"].value_counts().head(25).reset_index()
        counts.columns = ["artist", "count"]

        st.caption("Top artists by track appearances (lead artist, top 25)")
        base = alt.Chart(counts).encode(y=alt.Y("artist:N", sort='-x', title=None))
        stems = base.mark_rule(color="#a5d6a7").encode(
            x=alt.X("count:Q", title="Tracks"),
            x2=alt.value(0)
        )
        # subtle hover grow
        hover = alt.selection_single(fields=["artist"], on="mouseover", nearest=True, empty="none")
        dots = base.add_selection(hover).mark_circle(color=PRIMARY, opacity=0.95).encode(
            x="count:Q",
            size=alt.condition(hover, alt.value(600), alt.value(220)),
            tooltip=["artist:N", "count:Q"]
        )
        st.altair_chart((stems + dots).properties(height=520), use_container_width=True)

# ---- Time tab ----
with tab_time:
    if need_analysis():
        st.info("Analyze a playlist to view Time visuals.")
    else:
        tracks_df = st.session_state["tracks_df"]
        enriched = st.session_state["enriched"]

        td = tracks_df.dropna(subset=["release_year"]).copy()
        td["decade"] = (td["release_year"] // 10) * 10
        decade_counts = td.groupby(["decade"]).size().reset_index(name="count")

        st.subheader("Timeline by decade")
        if not decade_counts.empty:
            area = alt.Chart(decade_counts).mark_area(opacity=0.7, color=FILL).encode(
                x=alt.X("decade:O", title="Decade"),
                y=alt.Y("count:Q", title="Tracks"),
                tooltip=["decade","count"]
            ).properties(height=260)
            st.altair_chart(area, use_container_width=True)
        else:
            st.info("No release year data available.")

        st.subheader("Artist × Year heatmap")
        if not td.empty:
            ay = enriched.dropna(subset=["release_year"]).copy()
            ay["lead_artist"] = ay["artist"].str.split(", ").str[0]
            top12 = ay["lead_artist"].value_counts().head(12).index.tolist()
            ay = ay[ay["lead_artist"].isin(top12)]
            heat = alt.Chart(ay).mark_rect().encode(
                x=alt.X("release_year:O", title="Year"),
                y=alt.Y("lead_artist:N", sort='-x', title="Artist"),
                color=alt.Color("count():Q", title="Tracks",
                                scale=alt.Scale(range=PALETTE[::-1])),
                tooltip=["lead_artist", "release_year", alt.Tooltip("count():Q", title="Tracks")]
            ).properties(height=340)
            st.altair_chart(heat, use_container_width=True)
        else:
            st.info("Not enough year data for heatmap.")

# ---- Popularity tab ----
with tab_pop:
    if need_analysis():
        st.info("Analyze a playlist to view Popularity.")
    else:
        tracks_df = st.session_state["tracks_df"]
        pop = tracks_df.dropna(subset=["popularity"])
        chart_pop = alt.Chart(pop).mark_bar(color=PRIMARY).encode(
            x=alt.X("popularity:Q", bin=alt.Bin(maxbins=20), title="Popularity (0–100)"),
            y=alt.Y("count():Q", title="Tracks"),
            tooltip=[alt.Tooltip("count():Q", title="Tracks")]
        ).properties(height=300)
        st.altair_chart(chart_pop, use_container_width=True)

        td2 = tracks_df.dropna(subset=["release_year"]).copy()
        st.subheader("Popularity vs. year")
        if not td2.empty:
            pop_scatter = alt.Chart(td2).mark_circle(color=SECONDARY, opacity=0.75).encode(
                x=alt.X("release_year:O", title="Year"),
                y=alt.Y("popularity:Q", title="Popularity"),
                size=alt.Size("count():Q", legend=None),
                tooltip=["name","artist","album","release_year","popularity"]
            ).properties(height=320)
            st.altair_chart(pop_scatter, use_container_width=True)
        else:
            st.info("No release years available for scatter plot.")

# ---- Covers tab (clean grid, stable order) ----
with tab_cov:
    if need_analysis():
        st.info("Analyze a playlist to view covers.")
    else:
        tracks_df = st.session_state["tracks_df"]
        thumbs_all = tracks_df.dropna(subset=["image"]).copy()
        if not thumbs_all.empty:
            st.caption("Album covers (neatly aligned)")
            idxs = st.session_state.get("covers_idx", list(thumbs_all.index))
            thumbs = thumbs_all.loc[idxs[:min(24, len(idxs))]].reset_index(drop=True)
            n_cols = 6
            cols = st.columns(n_cols)
            for i, row in thumbs.iterrows():
                with cols[i % n_cols]:
                    st.image(row["image"], use_column_width=True)
        else:
            st.info("No cover art found for this playlist.")

# ---- Companion (AI) tab ----
with tab_ai:
    if need_analysis():
        st.info("Analyze a playlist to view the AI companion.")
    else:
        tracks_df = st.session_state["tracks_df"]
        enriched = st.session_state["enriched"]

        st.subheader("Playlist Companion (AI)")
        vibe_hint = st.text_input(
            "Optional: nudge the description (e.g., 'moody late-night drive', 'high-energy gym mix')", ""
        )
        stats = compute_stats(tracks_df, enriched)
        text = llm_vibe_summary(stats, vibe_hint=vibe_hint) or build_rule_based_summary(stats)
        st.write(text)
        st.caption("If no OpenAI key is configured, a smart rule-based summary is used.")

# ---- Export tab ----
with tab_export:
    if need_analysis():
        st.info("Analyze a playlist to export data.")
    else:
        tracks_df = st.session_state["tracks_df"]
        enriched = st.session_state["enriched"]
        st.write("Download your data:")
        st.download_button(
            "Tracks CSV",
            tracks_df.to_csv(index=False).encode(),
            file_name="playlist_tracks.csv",
            mime="text/csv"
        )
        if "artist_name" in enriched.columns:
            export_art = (
                enriched[["artist_id","artist_name","genres","artist_popularity"]]
                .drop_duplicates(subset=["artist_id"])
            )
            st.download_button(
                "Artists CSV",
                export_art.to_csv(index=False).encode(),
                file_name="artists.csv",
                mime="text/csv"
            )
