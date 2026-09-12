from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from video_info import VideoInfoError, fetch_metadata, is_youtube_url  # noqa: E402

app = FastAPI(title="YouTube video info API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class VideoRequest(BaseModel):
    url: str


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/video-info")
def video_info(body: VideoRequest):
    url = (body.url or "").strip()
    if not url:
        return JSONResponse({"error": "URL is required"}, status_code=400)
    if not is_youtube_url(url):
        return JSONResponse(
            {"error": "URL must be a youtube.com or youtu.be link"},
            status_code=400,
        )
    try:
        return fetch_metadata(url)
    except VideoInfoError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
