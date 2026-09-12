"use client";

import { FormEvent, useState } from "react";

type VideoInfo = {
  title: string | null;
  duration: number | null;
  view_count: number | null;
  upload_date: string | null;
};

function formatDuration(seconds: number | null): string {
  if (seconds == null || Number.isNaN(seconds)) return "—";
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = total % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
  }
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

function formatViews(count: number | null): string {
  if (count == null || Number.isNaN(count)) return "—";
  return count.toLocaleString();
}

function formatUploadDate(ymd: string | null): string {
  if (!ymd || !/^\d{8}$/.test(ymd)) return ymd ?? "—";
  const date = new Date(
    `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}T00:00:00Z`,
  );
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<VideoInfo | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);

    try {
      const response = await fetch("/api/video-info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = (await response.json()) as VideoInfo & { error?: string };
      if (!response.ok) {
        setError(data.error || "Request failed");
        return;
      }
      setInfo(data);
    } catch {
      setError("Could not reach the API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-16">
      <main className="w-full max-w-xl rounded-xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <h1 className="text-2xl font-semibold tracking-tight">YouTube video info</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          Paste a YouTube URL to fetch title, duration, views, and upload date.
        </p>

        <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-3 sm:flex-row">
          <input
            type="url"
            name="url"
            required
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            className="min-w-0 flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {loading ? "Fetching…" : "Fetch"}
          </button>
        </form>

        {error && (
          <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        {info && (
          <dl className="mt-6 grid gap-3 text-sm">
            <div>
              <dt className="text-zinc-500">Title</dt>
              <dd className="font-medium">{info.title ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Duration</dt>
              <dd className="font-medium">{formatDuration(info.duration)}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Views</dt>
              <dd className="font-medium">{formatViews(info.view_count)}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Upload date</dt>
              <dd className="font-medium">{formatUploadDate(info.upload_date)}</dd>
            </div>
          </dl>
        )}
      </main>
    </div>
  );
}
