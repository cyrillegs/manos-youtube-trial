#!/usr/bin/env python3
"""Turn a topic into a raw mp4: LLM script -> per-scene YouTube b-roll (yt-dlp) ->
per-scene TTS narration -> burned captions -> concat -> background music.

Styled after trial #1's scripts/video_info.py: stdlib-first, argparse CLI, a
VideoGenError exception, prints clean JSON, optional --out. See PLAN.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT = 1080, 1920  # vertical, matches modern short-form output
MIN_SCENE_SECONDS = 3.0


class VideoGenError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def load_dotenv(path: Path) -> None:
    """Tiny stdlib .env loader — no python-dotenv dependency needed for a CLI script."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def fail(message: str, code: int = 1) -> None:
    print(json.dumps({"error": message}), file=sys.stdout)
    raise SystemExit(code)


def openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise VideoGenError("OPENROUTER_API_KEY is not set")
    return key


def extract_json_object(text: str) -> dict:
    """Defensive JSON extraction: pull the first {...} block out of LLM prose,
    the same defensive posture video_info.py takes toward upstream responses."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise VideoGenError(f"No JSON object found in model output: {text[:200]}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise VideoGenError(f"Model output was not valid JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Stage 1: script generation
# ---------------------------------------------------------------------------

def generate_script(topic: str, scene_count: int = 3) -> dict:
    model = os.environ.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
    system = (
        "You write short video narration scripts. Given a topic, respond with ONLY a "
        "JSON object (no prose, no markdown fences) of the shape: "
        '{"title": "<short title>", "scenes": ['
        '{"text": "<one narration sentence>", "keywords": "<a short YouTube search '
        'phrase for stock/b-roll footage matching this sentence>"}, ...]}. '
        f"Write exactly {scene_count} scenes. Keep each narration sentence under 20 words."
    )
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": topic},
                ],
            },
            timeout=60,
        )
    except requests.RequestException as exc:
        raise VideoGenError(f"OpenRouter chat request failed: {exc}") from exc
    if not res.ok:
        raise VideoGenError(f"OpenRouter chat error {res.status_code}: {res.text[:300]}")

    data = res.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if not content:
        raise VideoGenError("OpenRouter returned no script text")

    parsed = extract_json_object(content)
    scenes = parsed.get("scenes") or []
    if not scenes:
        raise VideoGenError("Script JSON had no scenes")
    return {"title": parsed.get("title") or topic, "scenes": scenes}


# ---------------------------------------------------------------------------
# Stage 2: b-roll (real YouTube footage via yt-dlp), with a Pillow fallback
# ---------------------------------------------------------------------------

def _skip_intro_range(info: dict) -> dict:
    total = info.get("duration") or 0
    start = min(10.0, max(0.0, total * 0.1)) if total else 0.0
    end = min(start + 8, total) if total else start + 8
    if end - start < 3:  # very short video — just take what's there
        start, end = 0.0, min(8.0, total) if total else 8.0
    return {"start_time": start, "end_time": end}


def fetch_broll(keywords: str, out_dir: Path) -> Path:
    """Search for candidate clips first (cheap, no download), then try downloading
    each one in turn until one actually works. A single top result being removed/
    format-restricted (common — confirmed in testing) used to fail the whole scene
    on the first bad pick; trying a few candidates is much more resilient."""
    try:
        import yt_dlp
    except ImportError as exc:
        raise VideoGenError("yt-dlp is not installed. Run: pip install -r requirements.txt") from exc

    # Same fix trial #1's video_info.py already proved necessary: the default
    # ("web") client no longer exposes downloadable progressive formats — confirmed
    # by testing (every "web"-only format came back acodec=none, and a plain
    # format selector failed with "Requested format is not available" even though
    # formats existed). android/ios/tv clients expose real combined formats.
    YT_CLIENT_ARGS = {"youtube": {"player_client": ["android", "ios", "tv", "web"]}}

    search_opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "extractor_args": YT_CLIENT_ARGS}
    try:
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            search = ydl.extract_info(f"ytsearch5:{keywords}", download=False)
    except Exception as exc:  # noqa: BLE001
        raise VideoGenError(f"yt-dlp search failed: {exc}") from exc

    video_ids = [e["id"] for e in (search or {}).get("entries") or [] if e and e.get("id")]
    if not video_ids:
        raise VideoGenError(f"No search results for: {keywords}")

    last_error = "no candidates tried"
    for video_id in video_ids:
        out_path = out_dir / f"broll-{uuid.uuid4().hex[:8]}.mp4"
        dl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "best[height<=480][ext=mp4]/best[height<=480]/best",
            "outtmpl": str(out_path.with_suffix("")) + ".%(ext)s",
            # Skip likely intro/branding cards by starting a bit into the video
            # (confirmed by inspecting an actual extracted frame — an 0-8s grab
            # landed on a publisher logo card, not real content) — 10% in, capped
            # to a 5-15s window so it stays safe on short clips too.
            "download_ranges": lambda info, ydl: [_skip_intro_range(info)],
            "force_keyframes_at_cuts": True,
            "extractor_args": YT_CLIENT_ARGS,
        }
        try:
            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            candidates = list(out_dir.glob(f"{out_path.stem}.*"))
            if candidates:
                return candidates[0]
            last_error = f"{video_id}: download reported success but produced no file"
        except Exception as exc:  # noqa: BLE001 — try the next candidate
            last_error = f"{video_id}: {exc}"
            continue

    raise VideoGenError(f"All {len(video_ids)} b-roll candidates failed for '{keywords}': {last_error}")


def render_fallback_slide(text: str, out_dir: Path, duration: float) -> Path:
    """A plain color background, so one bad b-roll search doesn't fail the whole
    video. Deliberately NO caption text here — build_scene_clip() burns the caption
    on top of every scene (b-roll or fallback) uniformly; drawing it here too caused
    a visibly duplicated, off-screen caption in testing."""
    out_path = out_dir / f"slide-{uuid.uuid4().hex[:8]}.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x1F2937:s={WIDTH}x{HEIGHT}:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration),
        str(out_path),
    ]
    run_ffmpeg(cmd, "fallback slide render")
    return out_path


def wrap_caption(text: str, chars_per_line: int = 26) -> str:
    """drawtext doesn't auto-wrap — without this, a full sentence overruns the
    frame on both sides (confirmed by inspecting an actual rendered frame)."""
    import textwrap
    return "\n".join(textwrap.wrap(text, width=chars_per_line)) or text


def pick_font_file() -> str:
    for candidate in (
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ):
        if Path(candidate).exists():
            return candidate
    raise VideoGenError("No usable bold font file found for caption rendering")


def escape_ffmpeg_path(path: str) -> str:
    """Escape a Windows drive-letter colon for use inside an ffmpeg filter option
    value (e.g. fontfile=, textfile=) — learned the hard way earlier: unescaped,
    ffmpeg's filtergraph parser reads the colon as an option separator."""
    return path.replace("\\", "/").replace(":", r"\:")


def run_ffmpeg(cmd: list[str], step: str) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoGenError(f"ffmpeg failed at {step}: {proc.stderr[-800:]}")


def ffprobe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        raise VideoGenError(f"Could not read duration of {path}: {proc.stderr[-300:]}")


# ---------------------------------------------------------------------------
# Stage 3: narration TTS — OpenRouter primary, ElevenLabs fallback
# ---------------------------------------------------------------------------

def pick_openrouter_tts_model() -> str:
    forced = os.environ.get("OPENROUTER_TTS_MODEL", "").strip()
    if forced:
        return forced
    try:
        res = requests.get(
            "https://openrouter.ai/api/v1/models",
            params={"output_modalities": "audio"},
            headers={"Authorization": f"Bearer {openrouter_key()}"},
            timeout=20,
        )
        res.raise_for_status()
        models = res.json().get("data", [])
    except requests.RequestException as exc:
        raise VideoGenError(f"Could not list OpenRouter audio models: {exc}") from exc
    if not models:
        raise VideoGenError("OpenRouter has no audio-output models available right now")

    def price(m: dict) -> float:
        try:
            return float((m.get("pricing") or {}).get("completion", "999"))
        except (TypeError, ValueError):
            return 999.0

    models.sort(key=price)
    return models[0]["id"]


def synthesize_voice_openrouter(text: str, out_path: Path) -> None:
    model = pick_openrouter_tts_model()
    res = requests.post(
        "https://openrouter.ai/api/v1/audio/speech",
        headers={
            "Authorization": f"Bearer {openrouter_key()}",
            "Content-Type": "application/json",
        },
        json={"model": model, "input": text, "voice": "alloy", "response_format": "mp3"},
        timeout=60,
    )
    if not res.ok:
        raise VideoGenError(f"OpenRouter TTS error {res.status_code}: {res.text[:300]}")
    out_path.write_bytes(res.content)


def synthesize_voice_elevenlabs(text: str, out_path: Path) -> None:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if not key or not voice_id:
        raise VideoGenError("ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID not set for TTS fallback")
    res = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": key, "content-type": "application/json", "accept": "audio/mpeg"},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.75},
        },
        timeout=60,
    )
    if not res.ok:
        raise VideoGenError(f"ElevenLabs TTS error {res.status_code}: {res.text[:300]}")
    out_path.write_bytes(res.content)


def synthesize_voice(text: str, out_path: Path) -> None:
    try:
        synthesize_voice_openrouter(text, out_path)
        return
    except VideoGenError as primary_err:
        if os.environ.get("ELEVENLABS_API_KEY"):
            synthesize_voice_elevenlabs(text, out_path)
            return
        raise primary_err


# ---------------------------------------------------------------------------
# Stage 4: per-scene clip (trim/loop visual to narration length, burn caption, mux)
# ---------------------------------------------------------------------------

def build_scene_clip(visual: Path, audio: Path, caption_text: str, duration: float, out_dir: Path) -> Path:
    out_path = out_dir / f"scene-{uuid.uuid4().hex[:8]}.mp4"
    txt_file = out_dir / f"caption-{uuid.uuid4().hex[:8]}.txt"
    txt_file.write_text(wrap_caption(caption_text), encoding="utf-8")
    fontfile = pick_font_file()

    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"drawtext=fontfile='{escape_ffmpeg_path(fontfile)}':textfile='{escape_ffmpeg_path(str(txt_file))}':"
        "fontcolor=white:fontsize=56:line_spacing=10:box=1:boxcolor=black@0.55:boxborderw=18:"
        # Anchor to a bottom margin (not a fixed y) so a longer, more-wrapped
        # caption still fits fully on screen instead of running past the frame.
        "x=(w-text_w)/2:y=h-text_h-160"
    )
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(visual),
        "-i", str(audio),
        "-t", str(duration),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(out_path),
    ]
    run_ffmpeg(cmd, "scene clip build")
    return out_path


# ---------------------------------------------------------------------------
# Stage 5-6: concat + procedural background music
# ---------------------------------------------------------------------------

def concat_scenes(clips: list[Path], out_dir: Path) -> Path:
    out_path = out_dir / "concat.mp4"
    list_file = out_dir / "concat_list.txt"
    # NOTE: the concat demuxer's file list is a different parser than a filtergraph
    # option value — it does NOT want escape_ffmpeg_path's colon-escaping (that
    # corrupts the path here, e.g. "C:/x" -> "C\:/x" which ffmpeg can't open).
    # Just forward-slash the path and escape a literal single quote if present.
    list_file.write_text(
        "\n".join(
            "file '{}'".format(str(c).replace("\\", "/").replace("'", r"'\''"))
            for c in clips
        ),
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(out_path),
    ]
    run_ffmpeg(cmd, "scene concat")
    return out_path


def add_background_music(video: Path, out_dir: Path) -> Path:
    out_path = out_dir / "final.mp4"
    duration = ffprobe_duration(video)
    # Procedural ambient bed — two detuned low sine tones, no licensed track needed.
    music_filter = (
        f"aevalsrc=0.05*sin(2*PI*110*t)+0.04*sin(2*PI*138*t):s=44100:d={duration}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-f", "lavfi", "-i", music_filter,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.5[aout]",
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac",
        str(out_path),
    ]
    run_ffmpeg(cmd, "background music mix")
    return out_path


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "video"


def generate_video(topic: str) -> dict:
    script = generate_script(topic)
    media_dir = ROOT / "backend" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="videogen-") as tmp:
        tmp_dir = Path(tmp)
        clips: list[Path] = []
        scene_summaries = []

        for i, scene in enumerate(script["scenes"]):
            text = scene["text"]
            keywords = scene.get("keywords") or text

            audio_path = tmp_dir / f"voice-{i}.mp3"
            synthesize_voice(text, audio_path)
            duration = max(ffprobe_duration(audio_path), MIN_SCENE_SECONDS)

            source_url = None
            try:
                visual_path = fetch_broll(keywords, tmp_dir)
                source_url = f"ytsearch1:{keywords}"
            except VideoGenError:
                visual_path = render_fallback_slide(text, tmp_dir, duration)

            clip = build_scene_clip(visual_path, audio_path, text, duration, tmp_dir)
            clips.append(clip)
            scene_summaries.append({"text": text, "keywords": keywords, "source_url": source_url})

        concatenated = concat_scenes(clips, tmp_dir)
        final_tmp = add_background_music(concatenated, tmp_dir)

        slug = slugify(script["title"])
        final_path = media_dir / f"{slug}-{uuid.uuid4().hex[:6]}.mp4"
        final_path.write_bytes(final_tmp.read_bytes())

    return {
        "title": script["title"],
        "scenes": scene_summaries,
        "video_path": str(final_path),
        "duration_seconds": ffprobe_duration(final_path),
    }


def main() -> None:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Generate a raw mp4 from a topic")
    parser.add_argument("topic", help="Video topic")
    parser.add_argument("--out", metavar="PATH", help="Also write the JSON summary to this file")
    args = parser.parse_args()

    topic = (args.topic or "").strip()
    if not topic:
        fail("Topic is required")

    try:
        payload = generate_video(topic)
    except VideoGenError as exc:
        fail(str(exc), exc.code)

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
