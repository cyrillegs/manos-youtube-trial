# Automated video generator

Manos Corp full-stack trial #2: topic in, raw mp4 out. Lives in
`trial-2-video-generator/` next to trial #1 (`trial-1-youtube-metadata/`).
Commands below assume you're `cd`'d into this folder.

## How it works

1. OpenRouter writes a short script (title + 3 narration scenes + search keywords).
2. yt-dlp pulls a few seconds of YouTube b-roll per scene (Pillow slide if search fails).
3. ElevenLabs narrates each scene (OpenRouter TTS was not actually callable).
4. ffmpeg burns captions, concatenates scenes, mixes a procedural music bed.
5. FastAPI serves the mp4; Next.js proxies `{topic}` to that API and plays the file.

## Run locally

Copy [`.env.example`](.env.example) to `.env` and set `OPENROUTER_API_KEY`,
`ELEVENLABS_API_KEY`, and `ELEVENLABS_VOICE_ID`.

CLI (no HTTP):

```bash
python -m pip install -r requirements.txt
python scripts/video_generator.py "how volcanoes are formed"
```

Backend (port 8000):

```bash
python -m pip install -r backend/requirements.txt
cd backend
python -m uvicorn main:app --reload --port 8000
```

Frontend (port 3000):

```bash
cd web
# .env.local with BACKEND_URL=http://localhost:8000
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Generation takes ~30–90s.

## Write-up

See [WRITEUP.md](WRITEUP.md).

## Deploy

Dockerfiles are in `backend/Dockerfile` and `web/Dockerfile` (build context = this
folder). ffmpeg and DejaVu fonts are in the API image for captions. Set
`BACKEND_URL` as a **build arg** on the frontend (rewrites `/media` to the API).
A VPS datacenter IP will likely bot-block yt-dlp b-roll the same way trial 1 did
for metadata — fallback slides still produce an mp4. Not deployed in this 2-hour
window.
