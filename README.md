# PodDigest

Personalized podcast digest service. Subscribe to shows, set your interests,
and get a single audio briefing covering all new episodes — delivered via
web player or private RSS feed for Apple Podcasts.

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # add your API keys
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Environment Variables

| Variable | Description |
|----------|-------------|
| ANTHROPIC_API_KEY | Claude API key |
| OPENAI_API_KEY | Whisper + TTS key |
| DATABASE_URL | SQLite path (default: ./podcast_digest.db) |
| AUDIO_STORAGE_PATH | Where MP3s are saved (default: ./digests) |
| BASE_URL | Public URL of backend (for RSS feed enclosure URLs) |

## Usage

1. Add shows via Search, RSS URL, or OPML import
2. Set your interest topics and description
3. Choose schedule (weekly / biweekly / on new episodes)
4. Click "Generate Digest" to create your first digest
5. Copy the RSS Feed URL to subscribe in Apple Podcasts
