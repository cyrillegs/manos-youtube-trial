# YouTube video info

Manos Corp full-stack trial: a Python/yt-dlp API and a Next.js frontend as two services.

## Run locally

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
# optional: create .env.local with BACKEND_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), paste a YouTube URL, and click Fetch. The Next.js route `/api/video-info` proxies to the Python API.

## Deploy (Dokploy)

Two applications, same GitHub repo:

| Service | Dockerfile | Port | Env |
| --- | --- | --- | --- |
| Backend | `backend/Dockerfile` | 8000 | — |
| Frontend | `web/Dockerfile` | 3000 | `BACKEND_URL=https://<backend-host>` |

## Write-up

See [WRITEUP.md](WRITEUP.md).
