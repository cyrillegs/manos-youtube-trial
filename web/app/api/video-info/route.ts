import { spawn } from "child_process";
import path from "path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const YOUTUBE_HOSTS = new Set([
  "youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "youtu.be",
]);

type VideoInfo = {
  title: string | null;
  duration: number | null;
  view_count: number | null;
  upload_date: string | null;
};

function isYouTubeUrl(url: string): boolean {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "").toLowerCase();
    return YOUTUBE_HOSTS.has(host);
  } catch {
    return false;
  }
}

function runVideoInfo(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const python = process.env.PYTHON_BIN || "python";
    const script = path.resolve(process.cwd(), "..", "scripts", "video_info.py");
    const child = spawn(python, [script, url], { windowsHide: true });

    let stdout = "";
    let stderr = "";
    let settled = false;

    const finish = (err?: Error, result?: string) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (err) reject(err);
      else resolve(result ?? "");
    };

    const timer = setTimeout(() => {
      child.kill();
      finish(new Error("Timed out fetching video metadata (20s)"));
    }, 20_000);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (err) => {
      finish(
        new Error(
          `Could not start Python (${python}): ${err.message}. Set PYTHON_BIN if needed.`,
        ),
      );
    });
    child.on("close", (code) => {
      if (code !== 0) {
        try {
          const parsed = JSON.parse(stdout) as { error?: string };
          if (parsed.error) {
            finish(new Error(parsed.error));
            return;
          }
        } catch {
          // fall through to stderr / exit code
        }
        finish(new Error(stderr.trim() || `Python exited with code ${code}`));
        return;
      }
      finish(undefined, stdout);
    });
  });
}

export async function POST(request: Request) {
  let body: { url?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Request body must be JSON" }, { status: 400 });
  }

  const url = typeof body.url === "string" ? body.url.trim() : "";
  if (!url) {
    return NextResponse.json({ error: "URL is required" }, { status: 400 });
  }
  if (!isYouTubeUrl(url)) {
    return NextResponse.json(
      { error: "URL must be a youtube.com or youtu.be link" },
      { status: 400 },
    );
  }

  try {
    const stdout = await runVideoInfo(url);
    const data = JSON.parse(stdout) as VideoInfo & { error?: string };
    if (data.error) {
      return NextResponse.json({ error: data.error }, { status: 502 });
    }
    return NextResponse.json({
      title: data.title ?? null,
      duration: data.duration ?? null,
      view_count: data.view_count ?? null,
      upload_date: data.upload_date ?? null,
    } satisfies VideoInfo);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to fetch video metadata";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
