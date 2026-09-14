# Trial write-up

## AI tooling

I used Cursor. I asked it to turn the PDF into a plan, then to implement the Python pipeline, FastAPI wrapper, and Next.js page. I supplied API keys, chose OpenRouter for the script and ElevenLabs for TTS after OpenRouter speech failed, and ran real generations to inspect frames and audio. I did not hand-write the pipeline from scratch.

## If this were production

I would not generate video inside an HTTP request. A worker queue would own yt-dlp, TTS, and ffmpeg, with a hard timeout, one job per topic, and the mp4 stored in object storage (R2/S3) instead of the API disk. B-roll from a VPS will hit the same YouTube datacenter bot-block as trial 1 — there is no Data API equivalent for downloading clips, so production footage should come from a licensed stock API or a residential proxy. Cache by topic/script hash. Pin `yt-dlp` and ffmpeg. Keep secrets out of git. Rate-limit so one client cannot burn TTS and YouTube.

## What broke

OpenRouter's `/api/v1/audio/speech` looks documented but is not usable: live `output_modalities=audio` listed four models (two are music-gen, not TTS) and the two speech-looking slugs both returned `400 Model does not exist`. Docs example slugs were stale too. After ~10 minutes I swapped to ElevenLabs, which returned a real mp3 with a measurable duration.

yt-dlp format selection failed with "Requested format is not available" even though formats existed. The default client only exposes `acodec=none` streams. Same fix as trial 1: `extractor_args` with `android`/`ios`/`tv`/`web` on every yt-dlp call.

Downloading 0–8s sometimes landed on a publisher logo card (confirmed by extracting a frame). The range now starts ~10% in (capped at 10s). Search tries `ytsearch5` candidates in turn, not just the first hit.

Captions ran off both edges and were drawn twice (baked into the fallback slide *and* as the overlay). Fallback slides are now plain; text is wrapped before `textfile=`; caption `y` is based on actual text height.

ffmpeg concat failed on Windows because filtergraph path escaping (`C\:/...`) was reused for the concat demuxer file list, which is a different parser. Concat now only slash-normalizes and quote-escapes.

The web app's `<video src="/media/...">` would 404 on the Next.js origin. A rewrite proxies `/media/*` to the Python API. Browser check: topic "how volcanoes are formed" → 200 in ~39s → h264 1080×1920 mp4 played in the page.

## What I'd add next

Real YouTube watch URLs on each scene instead of `ytsearch1:…`. A stock-footage source that survives a datacenter IP. Word-level captions. Job status instead of one long POST. Deploy the two services next to trial 1 on Dokploy if this were more than a 2-hour prototype.
