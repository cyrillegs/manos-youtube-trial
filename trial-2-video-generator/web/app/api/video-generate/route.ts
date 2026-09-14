import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Video generation runs a whole pipeline (LLM script, yt-dlp b-roll, TTS,
// ffmpeg) — far longer than trial #1's metadata fetch, so both the Next.js
// route budget and the outgoing fetch timeout need real headroom.
export const maxDuration = 300;

const backendUrl = () =>
  (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Request body must be JSON" }, { status: 400 });
  }

  try {
    const response = await fetch(`${backendUrl()}/video-generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(280_000),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Could not reach the backend API";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
