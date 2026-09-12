# Trial write-up

## AI tooling

I used Cursor for this task. I asked it to turn the PDF brief into a plan, then to implement that plan (Python CLI, Next.js page + API route that spawns the script, and this write-up). I supplied the YouTube URL, chose real Python wiring over a mock, and filled in Dokploy credentials. I did not hand-write the script or UI from scratch.

## If this were production

I would not spawn Python from a Next.js request on the same process. A small worker or HTTP service would own yt-dlp, with a hard timeout and process kill, URL allow-listing, caching by video id, and a rate limit so one client cannot burn YouTube/yt-dlp. The API would return a typed error contract, and the app would run as a container with pinned `yt-dlp` and no secrets in git.

## What broke

PowerShell `curl` sent a broken body (`Request body must be JSON`); a Python `urllib` POST worked. Next.js could not bind port 3000 (already in use) and fell back to 3001. Local yt-dlp returned metadata on the first try, including `/shorts/` URLs. On the Dokploy VPS, YouTube blocked the datacenter IP (`Sign in to confirm you’re not a bot`) for every video, not just Shorts. If yt-dlp is blocked, the API falls back to YouTube’s Android/iOS InnerTube player endpoint, which still returns title, duration, and views without cookies.
