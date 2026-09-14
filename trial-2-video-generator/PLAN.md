# Manos Corp — 2nd Trial Task: Automated Video Generator

## Progress — what's actually built right now

*Clock: 5:25–7:25 PM PH time. Pipeline + API were already verified before this stretch.
This update is after verifying the Next.js UI in the browser and writing the hand-in docs.*

**Done, verified:**
- [x] `requirements.txt` (`yt-dlp`, `requests`, `Pillow`)
- [x] `.env.example` — OpenRouter + ElevenLabs + Dokploy
- [x] `scripts/video_generator.py` — full pipeline, real mp4s (h264+aac, 1080x1920)
- [x] OpenRouter TTS live-checked and **swapped to ElevenLabs** (speech models 400 / do not exist)
- [x] yt-dlp `player_client` args, intro skip, `ytsearch5` candidate loop
- [x] Caption wrap / no double-draw; concat demuxer path escaping (not filtergraph escaping)
- [x] Background music mixed (volumedetect non-silent)
- [x] `backend/main.py` — `/health` ok, `POST /video-generate` returns JSON, `/media` serves mp4
- [x] `web/` — topic form, proxy route (`maxDuration` 300 / 280s timeout), `<video>` plays
      via `/media` rewrite to the Python API. Browser: topic "how volcanoes are formed"
      → POST 200 in ~39s → 1080x1920 mp4 played in the page
- [x] `web/.env.local` — `BACKEND_URL=http://localhost:8000`
- [x] `WRITEUP.md`
- [x] `README.md`

**Dockerfiles written, not deployed:**
- [x] `backend/Dockerfile` (ffmpeg + DejaVu fonts) and `web/Dockerfile`
- [ ] Dokploy live URL (lowest priority; VPS yt-dlp will likely bot-block b-roll)

## Context

Manos Corp's second trial ("2nd Trial Task .pdf", now in this folder) asks for a prototype
that takes a topic and produces a raw mp4 — real footage, images, voiceover, captions,
music, "whatever you can make it do in the time," inside a **hard 2-hour work cap** ("stop
and send us whatever you have, even if it is half done"). This repo also holds the first
trial (YouTube metadata) in its own sibling folder, `trial-1-youtube-metadata/` — same
employer, same submission thread, same repo, but **each trial now lives in its own
top-level folder** (Cyril Dave's call, to keep the two submissions cleanly separated for
review). This trial's code is fully self-contained under `trial-2-video-generator/` and
does not import or extend anything from `trial-1-youtube-metadata/` — it follows the same
*patterns* (argparse CLI style, FastAPI proxy shape, Next.js page shape) but as its own
copies, since the folders are now independent.

Decisions locked in with Cyril Dave:
- **Script**: an LLM (via OpenRouter) writes the narration from the topic.
- **Voiceover**: OpenRouter TTS first (Deepgram Flux TTS is free on OpenRouter's
  OpenAI-compatible `/api/v1/audio/speech` endpoint, same key as the LLM call) — **verify
  this endpoint works in the first 10 minutes** (see "De-risking the 2-hour clock" below)
  before building the rest of the pipeline around it.
- **Visuals**: real YouTube b-roll via yt-dlp (already a proven dependency in trial #1),
  matched per-scene by search keywords the LLM also produces.
- **Scope**: the CLI pipeline *and* minimal FastAPI + Next.js wiring, following Part 1's
  patterns but as fresh files under this folder.
- **Repo**: same repo as trial #1, in its own folder (`trial-2-video-generator/`) — no
  second repo (the PDF doesn't require one either way).

**Reality check on the 2-hour cap**: this pipeline (LLM script → per-scene YouTube search/
download → per-scene TTS → captions → music mix → ffmpeg assembly → API → UI) is a lot for
2 hours, especially now that the web app also needs a fresh `create-next-app` scaffold
(trial #1's `web/` isn't reusable in place anymore). The plan below is ordered so the first
milestone alone already satisfies the brief (topic in, mp4 out), and each later milestone
is an incremental bonus you can stop after at any point per the PDF's own "send whatever
you have" instruction.

## De-risking the 2-hour clock (lessons from a near-identical build)

Cyril Dave has already shipped a very similar pipeline (a different repo: AI product-ad
generator — topic/product → script → AI visuals → TTS narration → ffmpeg composite →
finished mp4, same OpenRouter-as-aggregator shape) and, in this same session, hand-built an
ffmpeg narration+caption composite end-to-end. Two things from that experience change how
this plan should be executed, not just what it says:

1. **Verify OpenRouter TTS FIRST, before writing any pipeline code around it.** It has not
   been used hands-on before (unlike OpenRouter chat/images, which have). Spend the first
   ~10 minutes on a single throwaway script: POST one short sentence to
   `/api/v1/audio/speech` with the Deepgram Flux slug (confirm exact slug via `ctx7`/
   OpenRouter docs at that moment — free-model slugs rotate), save the response, play/
   inspect it, confirm duration is measurable via `ffprobe`. **If it doesn't return clean
   audio inside ~10 minutes of trying**, fall back immediately to **ElevenLabs** instead of
   debugging further — it's a proven, already-working TTS call (`ELEVENLABS_API_KEY` +
   `ELEVENLABS_VOICE_ID` env vars, same shape as trial #1's env pattern), and the 2-hour
   clock is too short to gamble on an unfamiliar endpoint. Note the swap honestly in
   `WRITEUP.md` either way — that's normal, expected engineering judgment, not a failure.

2. **ffmpeg caption-burning gotchas already paid for**: this session hand-built a
   `drawtext`-with-timed-`enable` caption overlay and hit two real issues worth avoiding
   here — (a) commas inside a filter *option value* like `enable='between(t,X,Y)'` can get
   misread as filter-chain separators unless escaped or the graph is built with explicit
   `[label]` pads between filters rather than bare comma-chaining; (b) this Windows ffmpeg
   build (`ffmpeg version 9.0-full_build-www.gyan.dev`) does **not** support
   `-filter_complex_script` (the file-based alternative) despite it being documented
   upstream — pass the filter graph inline via `-filter_complex "$(cat file)"` (or build it
   as a plain string) instead of relying on that flag. This plan's step 4 below already
   calls for a **`textfile=` temp file for the caption text itself** (not the whole
   filtergraph) — that part of the original design was already the right call and avoids
   most of this; just don't reach for `-filter_complex_script` if the caption timing needs
   its own multi-filter chain later.

3. **yt-dlp will work fine locally (home IP) for the CLI milestone** — but trial #1 already
   proved YouTube bot-blocks the Contabo VPS's datacenter IP range for *any* yt-dlp request,
   not just metadata. That means if milestone 4–5 (FastAPI + Next.js, deployed to the VPS)
   is reached, b-roll *fetching* will likely hit the same wall trial #1's metadata fetching
   did — and unlike metadata, there's no YouTube Data API v3 equivalent for downloading
   actual clip footage, so there's no easy fallback this time. Not a blocker for the 2-hour
   build itself (milestone 1–3 run locally), but worth flagging in `WRITEUP.md`'s "if this
   were production" section rather than being surprised by it later — e.g., a
   residential/rotating proxy, or a different footage source (a licensed stock API) would
   be the real fix.

## What's already available (no new global installs needed)

- `ffmpeg` is installed and on PATH (machine-wide).
- `requests` and `Pillow` are already installed in the Python environment (Pillow used
  only as a fallback if a scene's b-roll fetch fails, so one flaky search doesn't sink the
  whole video).
- `yt-dlp` is proven to work locally (per trial #1's `WRITEUP.md`: "Local yt-dlp returned
  metadata on the first try") — still needs listing in this folder's own
  `requirements.txt` since it's a separate deployable unit now.
- New requirement: an `OPENROUTER_API_KEY` in `trial-2-video-generator/.env` — trial #1's
  `.env` (which now lives at `trial-1-youtube-metadata/.env`) doesn't cover this.
- Fallback requirement (only if step 1 of "De-risking" above triggers it): an
  `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` in the same `.env`.

## Files to add / change

All paths below are relative to this folder (`trial-2-video-generator/`).

**`requirements.txt`** (new, this folder's own — `yt-dlp` and `requests`; `Pillow` too if
not already covered machine-wide) and **`.env`** (new, this folder's own — holds
`OPENROUTER_API_KEY`, `ELEVENLABS_API_KEY`/`ELEVENLABS_VOICE_ID` as the TTS fallback, and
later `BACKEND_URL` for the Next.js side, same pattern as trial #1's `.env.example`).

**`scripts/video_generator.py`** (new, styled after trial #1's `scripts/video_info.py`:
stdlib-first, argparse CLI, a `VideoGenError` exception mirroring `VideoInfoError`, prints
clean JSON, optional `--out`):

1. `generate_script(topic) -> dict` — POST to OpenRouter chat completions
   (`https://openrouter.ai/api/v1/chat/completions`, `Authorization: Bearer
   {OPENROUTER_API_KEY}`) asking for strict JSON: a short `title` and **3–4** `scenes` to
   start (fewer scenes = faster first end-to-end proof; scale up only if time allows), each
   `{"text": <one narration sentence>, "keywords": <YouTube search phrase for that
   sentence>}`. Model name from `OPENROUTER_MODEL` env var (default to a current free/cheap
   chat model — confirm the exact slug via `ctx7` against OpenRouter's docs at
   implementation time, per the global context7 rule, since free-model slugs rotate).
   Parse defensively (extract the first `{...}` block) the same way `video_info.py` is
   defensive about upstream responses.

2. `fetch_broll(scene, out_dir) -> path` — `yt-dlp` search (`ytsearch3:{keywords}`), pick
   the first usable result, pull a short clip via yt-dlp's section-download
   (`download_ranges` for roughly the first 6–8s) at a low resolution
   (`best[height<=480]`) to keep fetch time down. **Resilience**: if search/download fails
   for a scene, fall back to a Pillow-rendered slide (scene text on a plain background)
   for just that scene instead of failing the whole video — keeps one bad search from
   sinking the run.

3. `synthesize_voice(text, out_path)` — POST to OpenRouter's `/api/v1/audio/speech`
   (`input=text`, model from `OPENROUTER_TTS_MODEL`, default the free Deepgram Flux TTS
   slug — confirmed working per "De-risking" step 1 above, or already swapped to
   ElevenLabs if that check failed). One call per scene, so each scene's audio duration
   drives that scene's visual duration (measured via `ffprobe`).

4. `build_scene_clip(visual, audio, caption_text, duration) -> mp4` — trim/scale the
   b-roll (or hold the fallback slide) to `duration`, mute its original audio, burn in the
   caption via ffmpeg `drawtext` reading from a temp `textfile=` (avoids `drawtext`'s
   quote/colon escaping problems — this part of the design is already correct, keep it),
   mux with the scene's narration track.

5. `concat_scenes(clips) -> full.mp4` — ffmpeg concat demuxer.

6. `add_background_music(video) -> final.mp4` — a procedural low-volume ambient bed
   generated via ffmpeg `lavfi` (no licensed track needed, no download), mixed well under
   the narration (e.g. `amix` with a low weight on the music input).

7. `generate_video(topic) -> dict` orchestrates 1–6, writes the mp4 under
   `backend/media/<slug>.mp4`, and returns `{title, scenes: [{text, keywords, source_url}],
   video_path, duration_seconds}`. CLI entry point prints this as JSON (same shape as trial
   #1's `video_info.py`'s `main()`), with `--out` to also save it.

**`backend/main.py`** (new FastAPI app, own `backend/Dockerfile` and
`backend/requirements.txt` if we get to deploying it — styled after trial #1's
`backend/main.py`, not shared with it):
- `app.mount("/media", StaticFiles(directory=ROOT / "backend" / "media"))` to serve
  generated mp4s.
- `POST /video-generate` — body `{topic: str}`, imports and calls
  `video_generator.generate_video`, returns the JSON summary plus a `video_url` built from
  the mount path. `backend/media/` is already covered by the root `.gitignore` (generated
  output, not source).

**`web/`** (new — this folder needs its own Next.js scaffold, trial #1's `web/` isn't
reusable in place anymore: `npx create-next-app@latest web --typescript --tailwind --eslint
--app` from inside `trial-2-video-generator/`, matching how trial #1's was bootstrapped).
Then, styled after trial #1's app:
- `web/app/api/video-generate/route.ts` (mirrors trial #1's
  `web/app/api/video-info/route.ts` proxy pattern): proxies `{topic}` to
  `${BACKEND_URL}/video-generate`, but with a much longer `AbortSignal.timeout` (video
  generation takes far longer than a metadata fetch — use ~180s, and set
  `export const maxDuration` generously too).
- `web/app/page.tsx` (mirrors trial #1's `page.tsx` structure/Tailwind classes): a topic
  input + "Generate" button, a loading state (this will visibly take a while — say so in
  the UI), then the returned title/script text and a `<video controls>` pointing at the
  backend's `video_url`.

## Time budget (hard 2-hour cap — track against this, not just the milestone list)

| Time elapsed | Target |
|---|---|
| 0:00–0:10 | Verify OpenRouter TTS works (or confirm the ElevenLabs swap); `.env` + `requirements.txt` in place |
| 0:10–0:25 | `generate_script()` returning clean JSON for a real topic |
| 0:25–0:45 | `fetch_broll()` + Pillow fallback, proven on 1 scene |
| 0:45–1:05 | `synthesize_voice()` wired in, duration-driven scene length |
| 1:05–1:30 | `build_scene_clip()` with burned captions, one full scene end-to-end |
| 1:30–1:45 | `concat_scenes()` + `add_background_music()` — **first real mp4 out. This is the minimum viable hand-in.** |
| 1:45–2:00 | Buffer / `backend/main.py` if time allows; stop here regardless and write `WRITEUP.md` |

If running behind at any checkpoint, cut scene count (3 → 2) before cutting a whole stage —
a shorter finished video beats a longer broken one, same principle the PDF states outright.

## Priority order (in case the real clock runs out)

1. `scripts/video_generator.py` working end-to-end from the CLI (topic → mp4) — this alone
   already answers the brief.
2. Captions burned in.
3. Background music mixed in.
4. `backend/main.py` endpoint + static serving.
5. `web/` scaffold + generate page + API route.

Stop wherever the 2 hours run out; the PDF explicitly says a rough, honest prototype beats
a polished one you didn't finish. Dockerfiles/deployment are out of scope for the
prototype hand-in (the PDF only asks for code + the mp4) — only worth doing if time is
left over after milestone 5.

## Verification

- Run the CLI directly from inside `trial-2-video-generator/`:
  `python scripts/video_generator.py "<topic>"` — check the JSON output and inspect the
  mp4 with `ffprobe` (has video + audio streams, expected duration).
- If milestones 4–5 are reached: start `backend` (`uvicorn backend.main:app --reload
  --port 8000`) and `web` (`npm run dev`), submit a topic through the page in the browser,
  and confirm the video plays.

## Not part of this build

Part 1 of the PDF (name/city/timezone, OnlineJobs.ph link, GitHub link, availability,
salary expectation, and the 3 written questions about production experience / a bug fix /
ffmpeg-yt-dlp-Playwright-Next.js-Postgres experience) is a personal application response —
that's yours to answer, not something to draft into the repo. Already drafted separately at
`part1-application.txt` in this folder, ready to post.

## Prerequisite before implementation starts

An `OPENROUTER_API_KEY` needs to be added to `trial-2-video-generator/.env` (get one at
https://openrouter.ai/keys) — trial #1's `.env` (now at
`trial-1-youtube-metadata/.env`) doesn't cover this. `.env` files are gitignored
repo-wide, so it's safe to hold secrets there. If the TTS fallback triggers, also add
`ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID`.
