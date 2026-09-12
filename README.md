# YouTube video info

Manos Corp full-stack trial: a Next.js frontend and a Python API as two services.

- Frontend: https://manos.cdlegaspi.site
- API: https://manos-api.cdlegaspi.site
- Repo: https://github.com/cyrillegs/manos-youtube-trial

Paste a YouTube watch or Shorts URL to get title, duration, views, and upload date.

## How it works

The UI posts to `/api/video-info`. Next.js proxies that to the Python service (`BACKEND_URL`).

The API prefers **YouTube Data API v3** when `YOUTUBE_API_KEY` is set (needed on a VPS — yt-dlp gets bot-blocked on datacenter IPs). If the key is missing or the Data API fails, it falls back to yt-dlp, then YouTube InnerTube.

## Run locally

Copy [`.env.example`](.env.example) to `.env` and set `YOUTUBE_API_KEY` (optional locally; yt-dlp usually works on a home IP).

Backend (port 8000):

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

CLI (same metadata, no HTTP):

```bash
python -m pip install -r requirements.txt
python scripts/video_info.py "https://www.youtube.com/watch?v=jNQXAC9IVRw"
```

Frontend (port 3000):

```bash
cd web
npm install
# optional: .env.local with BACKEND_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Deploy (Dokploy)

Same GitHub repo, two applications:

| Service | Dockerfile | Port | Env |
| --- | --- | --- | --- |
| Backend | `backend/Dockerfile` | 8000 | `YOUTUBE_API_KEY` |
| Frontend | `web/Dockerfile` | 3000 | `BACKEND_URL=https://manos-api.cdlegaspi.site` |

Restrict the Data API key to the VPS IP (`169.58.89.96`) and to **YouTube Data API v3** only. Do not commit `.env`.

## Write-up

See [WRITEUP.md](WRITEUP.md).
