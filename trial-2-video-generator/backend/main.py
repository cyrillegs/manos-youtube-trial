from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


_load_env(ROOT / ".env")

from video_generator import VideoGenError, generate_video  # noqa: E402

MEDIA_DIR = ROOT / "backend" / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Automated video generator API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


class VideoRequest(BaseModel):
    topic: str


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/video-generate")
def video_generate(body: VideoRequest):
    topic = (body.topic or "").strip()
    if not topic:
        return JSONResponse({"error": "Topic is required"}, status_code=400)
    try:
        result = generate_video(topic)
    except VideoGenError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)

    video_path = Path(result["video_path"])
    result["video_url"] = f"/media/{video_path.name}"
    return result
