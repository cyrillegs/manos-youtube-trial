"use client";

import { FormEvent, useState } from "react";

type Scene = { text: string; keywords: string; source_url: string | null };
type VideoResult = {
  title: string;
  scenes: Scene[];
  video_url: string;
  duration_seconds: number;
};

export default function Home() {
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VideoResult | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch("/api/video-generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const data = (await response.json()) as VideoResult & { error?: string };
      if (!response.ok) {
        setError(data.error || "Request failed");
        return;
      }
      setResult(data);
    } catch {
      setError("Could not reach the API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-16">
      <main className="w-full max-w-xl rounded-xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <h1 className="text-2xl font-semibold tracking-tight">Automated video generator</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          Give it a topic. It writes a script, finds real YouTube b-roll per scene,
          narrates it, burns captions, and mixes in music — takes 30–90s, unlike the
          YouTube metadata trial.
        </p>

        <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            name="topic"
            required
            placeholder="e.g. how volcanoes are formed"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            className="min-w-0 flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {loading ? "Generating… (30–90s)" : "Generate"}
          </button>
        </form>

        {error && (
          <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        {result && (
          <div className="mt-6 space-y-4">
            <h2 className="text-lg font-medium">{result.title}</h2>
            <video
              controls
              className="w-full max-w-[260px] rounded-lg border border-zinc-200 dark:border-zinc-800"
              src={result.video_url}
            />
            <dl className="grid gap-3 text-sm">
              {result.scenes.map((scene, i) => (
                <div key={i} className="border-t border-zinc-200 pt-2 dark:border-zinc-800">
                  <dd>{scene.text}</dd>
                  <dt className="mt-1 text-xs text-zinc-500">
                    b-roll: {scene.source_url ? scene.source_url : "fallback slide (no match found)"}
                  </dt>
                </div>
              ))}
            </dl>
          </div>
        )}
      </main>
    </div>
  );
}
