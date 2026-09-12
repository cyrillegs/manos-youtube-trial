# YouTube video info

Manos Corp full-stack trial: a Python/yt-dlp CLI plus a Next.js page that calls it.

## Run locally

```bash
python -m pip install -r requirements.txt
python scripts/video_info.py "https://www.youtube.com/watch?v=jNQXAC9IVRw" --out sample.json
```

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), paste a YouTube URL, and click Fetch.

Optional: set `PYTHON_BIN` if `python` is not on your PATH.

## Deploy (Dokploy)

The root `Dockerfile` installs Python + yt-dlp, builds the Next.js app, and starts it on port 3000. Point a Dokploy application at this GitHub repo, use **Dockerfile** as the build type, and set:

```
PYTHON_BIN=python3
```

## Write-up

See [WRITEUP.md](WRITEUP.md).
