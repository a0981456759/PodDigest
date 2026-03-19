# 🎙 PodDigest

A self-hosted, AI-powered podcast digest service. Subscribe to podcasts, select episodes, and get a personalized audio summary — automatically transcribed, summarized, and narrated by AI.

---

## Features

- 🎧 Subscribe to any podcast via RSS, iTunes search, or OPML import
- ✅ Select specific episodes across multiple shows for your digest
- 🤖 AI summarization tailored to your interests (Claude)
- 🎤 Full audio transcription (OpenAI Whisper)
- 🔊 Text-to-speech narration (OpenAI TTS)
- 📡 Private RSS feed — listen in Apple Podcasts, Overcast, Pocket Casts, etc.
- ⏰ Auto-schedule: generate digests weekly, biweekly, or when new episodes arrive
- 💰 Per-digest cost estimate displayed in the UI

---

## Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend |
| ffmpeg | Any | Audio chunking (for episodes >25 MB) |

### API Keys needed

| Service | Where to get | Used for |
|---------|-------------|---------|
| **OpenAI** | [platform.openai.com](https://platform.openai.com) | Whisper (transcription) + TTS (audio) |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) | Claude (summarization + script writing) |

> **Estimated cost per digest (3–5 episodes):** ~$1–3 USD

---

## Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/poddigest.git
cd poddigest
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file inside the `backend/` folder:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional — these have sensible defaults
DATABASE_URL=sqlite:///./podcast_digest.db
AUDIO_STORAGE_PATH=./digests
BASE_URL=http://localhost:8000
```

Start the backend:

```bash
uvicorn main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Windows + Conda Users

```bash
conda activate YOUR_ENV
conda install -c conda-forge ffmpeg
```

Use the included batch file to start the backend (fixes DLL path issues on Windows):

```
backend\start_backend.bat
```

---

## How to Use

1. **Add shows** — click `+ Add Show`, search by name or paste an RSS URL
2. **Browse episodes** — click any show in the sidebar to see its episodes
3. **Select episodes** — check the episodes you want (you can mix episodes from multiple shows)
4. **Generate** — click `▶ Generate from Selected`
5. **Listen** — use the built-in player, or copy the RSS Feed URL into any podcast app

### Listen on your phone

Copy the **RSS Feed URL** shown in the player and add it to your podcast app:

| App | How |
|-----|-----|
| Apple Podcasts | Library → `···` → Follow a Show → paste URL |
| Overcast | + → Add URL |
| Pocket Casts | + → Add Podcast by URL |
| AntennaPod | + → Add podcast → RSS URL |

---

## Cloud Deployment

### Railway (recommended, ~$5/month)

1. Push your repo to GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. **Backend service** — Root: `backend/`, Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Frontend service** — Root: `frontend/`, Build: `npm run build`, Start: `npx serve dist`
5. Add environment variables to the backend service (same as `.env`)
6. Set `BASE_URL` to your backend's Railway public URL

### Render (free tier available)

1. **Backend:** New Web Service → `backend/` → `uvicorn main:app --host 0.0.0.0 --port $PORT`
2. **Frontend:** New Static Site → `frontend/` → Build: `npm run build` → Publish dir: `dist`
3. Add env vars to the backend service
4. Note: Render free tier sleeps after 15 min of inactivity

---

## Settings Guide

| Setting | What it does |
|---------|-------------|
| **Topic Tags** | Preset or custom tags — AI scores each episode's relevance to these topics |
| **Interest Description** | Free-text description of your interests — personalizes summaries and script tone |
| **Output Language** | English or 繁體中文 |
| **Schedule** | Weekly / Biweekly / On new episodes / Manual only |

---

## Architecture

```
RSS Feed
   ↓
Download Audio  →  OpenAI Whisper (transcription)
                           ↓
                   Anthropic Claude (summarize each episode)
                           ↓
                   Anthropic Claude (write digest script)
                           ↓
                   OpenAI TTS (synthesize audio)
                           ↓
               Web Player  +  Private RSS Feed
```

**Backend:** FastAPI · SQLAlchemy · SQLite · APScheduler
**Frontend:** React 18 · Tailwind CSS · Vite
**AI:** Claude (claude-sonnet-4-20250514) · Whisper · OpenAI TTS

---

## Contributing

PRs welcome! Ideas:

- [ ] Docker / docker-compose setup
- [ ] Email / push notifications for new episodes
- [ ] Support for more TTS voices and providers
- [ ] Multi-user support with login
- [ ] Export digest as PDF transcript

---

## License

MIT
