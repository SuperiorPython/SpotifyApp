## 🟢 Playlist DNA

Discover what your playlists say about your music taste — visually.

Playlist Visual Footprint is a Streamlit-based web app that turns any public Spotify playlist into an interactive, data-driven dashboard.
No login required — just paste a playlist link and explore.

## 🎧 Features

🎵 Genre Footprint → Big green donut chart summarizing your top genres

👤 Artist Breakdown → Lollipop chart showing your most frequent artists

📅 Timeline View → Decade-by-decade and artist-by-year visualizations

⭐ Popularity Explorer → See how mainstream or niche your playlist really is

💿 Cover Gallery → Grid of album art pulled directly from your playlist

🤖 AI Vibe Summary → One-click GPT-powered description of your playlist’s mood (optional)

📊 Data Export → Download full track + artist details as CSV files

## 🧩 Tech Stack
### Layer	Tools & Frameworks
Frontend:
+ Streamlit
+ Altair  (interactive charts)

Backend:
+ Spotipy (using the Spotify Web API (Client Credentials Flow))
+ OpenAI API (optional vibe descriptions)
Language:
+ Python 3.10+

Hosting:
+ Streamlit Cloud
## 🌍 Try It Live
 Public Link: https://spotifyvisuals.streamlit.app

Paste any public Spotify playlist URL and watch it come to life.
No account connection, no authentication, completely free to use.

## 🧠 How It Works

Paste a Spotify playlist link (public only).

The app fetches metadata using the Spotify Web API.

It visualizes your playlist’s genre, artist, decade, and popularity data in real-time.

Optionally, the AI Companion (powered by OpenAI GPT models) generates a personalized vibe summary that captures your playlist’s mood and aesthetic.

Download results as CSVs or just enjoy the dashboard view.

## 📈 Example Vibe Output
2010s Throwbacks: “A lively throwback to the early 2010s — full of catchy choruses, upbeat dance hits, and polished pop-R&B production. This playlist captures the carefree energy of weekend parties, school dances, and long drives with friends. Expect nostalgic hooks, polished beats, and that unmistakable 2010s shine that defined an entire era of radio and club anthems.”
