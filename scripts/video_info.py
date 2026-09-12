#!/usr/bin/env python3
"""Fetch basic YouTube video metadata with yt-dlp and print it as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlparse


class VideoInfoError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def is_youtube_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False
    if host.startswith("www."):
        host = host[4:]
    return host in {"youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


def fail(message: str, code: int = 1) -> None:
    print(json.dumps({"error": message}), file=sys.stdout)
    raise SystemExit(code)


def fetch_metadata(url: str) -> dict:
    try:
        import yt_dlp
    except ImportError as exc:
        raise VideoInfoError("yt-dlp is not installed. Run: pip install -r requirements.txt") from exc

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise VideoInfoError(f"Could not fetch video metadata: {exc}") from exc
    except VideoInfoError:
        raise
    except Exception as exc:  # noqa: BLE001 — keep CLI/API errors as JSON
        raise VideoInfoError(f"Unexpected error: {exc}") from exc

    if not info:
        raise VideoInfoError("yt-dlp returned no metadata")

    # Playlists / multi-entry results should not slip through.
    if info.get("_type") == "playlist":
        raise VideoInfoError("URL points to a playlist, not a single video")

    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "upload_date": info.get("upload_date"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch YouTube video metadata as JSON")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--out", metavar="PATH", help="Also write JSON to this file")
    args = parser.parse_args()

    url = (args.url or "").strip()
    if not url:
        fail("URL is required")
    if not is_youtube_url(url):
        fail("URL must be a youtube.com or youtu.be link")

    try:
        payload = fetch_metadata(url)
    except VideoInfoError as exc:
        fail(str(exc), exc.code)
    text = json.dumps(payload, ensure_ascii=False)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")

    print(text)


if __name__ == "__main__":
    main()
