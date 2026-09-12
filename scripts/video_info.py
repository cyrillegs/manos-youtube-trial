#!/usr/bin/env python3
"""Fetch basic YouTube video metadata with yt-dlp and print it as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


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


def extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.strip("/")
    parts = [p for p in path.split("/") if p]

    if host == "youtu.be" and parts:
        return parts[0]
    if host.endswith("youtube.com"):
        qs_id = parse_qs(parsed.query).get("v", [None])[0]
        if qs_id:
            return qs_id
        if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
            return parts[1]
    return None


def fetch_via_ytdlp(url: str) -> dict:
    try:
        import yt_dlp
    except ImportError as exc:
        raise VideoInfoError("yt-dlp is not installed. Run: pip install -r requirements.txt") from exc

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extractor_args": {"youtube": {"player_client": ["android", "ios", "tv", "web"]}},
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise VideoInfoError("yt-dlp returned no metadata")
    if info.get("_type") == "playlist":
        raise VideoInfoError("URL points to a playlist, not a single video")

    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "upload_date": info.get("upload_date"),
    }


def fetch_via_innertube(video_id: str) -> dict:
    clients = (
        (
            "ANDROID",
            "20.10.38",
            "com.google.android.youtube/20.10.38 (Linux; U; Android 14) gzip",
            {"androidSdkVersion": 30},
        ),
        (
            "IOS",
            "20.10.4",
            "com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 17_4 like Mac OS X)",
            {"deviceMake": "Apple", "deviceModel": "iPhone16,2"},
        ),
    )
    last_error = "InnerTube returned no metadata"
    for name, version, user_agent, extra in clients:
        client = {"clientName": name, "clientVersion": version, "hl": "en", "gl": "US"}
        client.update(extra)
        body = {
            "context": {"client": client},
            "videoId": video_id,
            "contentCheckOk": True,
            "racyCheckOk": True,
        }
        request = Request(
            "https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": user_agent},
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            continue

        play = payload.get("playabilityStatus") or {}
        details = payload.get("videoDetails") or {}
        if play.get("status") != "OK" or not details.get("title"):
            last_error = play.get("reason") or play.get("status") or last_error
            continue

        duration = details.get("lengthSeconds")
        views = details.get("viewCount")
        micro = (payload.get("microformat") or {}).get("playerMicroformatRenderer") or {}
        raw_date = micro.get("uploadDate") or micro.get("publishDate") or ""
        upload_date = raw_date.replace("-", "")[:8] or None
        return {
            "title": details.get("title"),
            "duration": int(duration) if duration is not None and str(duration).isdigit() else None,
            "view_count": int(views) if views is not None and str(views).isdigit() else None,
            "upload_date": upload_date,
        }
    raise VideoInfoError(f"Could not fetch video metadata: {last_error}")


def fetch_metadata(url: str) -> dict:
    last_error: Exception | None = None
    try:
        return fetch_via_ytdlp(url)
    except Exception as exc:  # noqa: BLE001 — fall back when yt-dlp is bot-blocked
        last_error = exc

    video_id = extract_video_id(url)
    if video_id:
        try:
            return fetch_via_innertube(video_id)
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    message = str(last_error) if last_error else "Could not fetch video metadata"
    raise VideoInfoError(message)


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
