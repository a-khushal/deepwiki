"use client";

import { useEffect, useState } from "react";
import { getRepoStatus } from "@/lib/api";
import { Loader2, CheckCircle2, GitBranch, FileCode, Blocks, BookOpen } from "lucide-react";

interface LoadingStateProps {
  repoId: string;
  onComplete: () => void;
  onError: (error: string) => void;
}

const STAGES = [
  { key: "cloning", label: "Cloning repository", Icon: GitBranch },
  { key: "parsing", label: "Parsing source code", Icon: FileCode },
  { key: "chunking", label: "Chunking code", Icon: Blocks },
  { key: "embedding", label: "Generating embeddings", Icon: Loader2 },
  { key: "docs", label: "Generating documentation", Icon: BookOpen },
];

export default function LoadingState({ repoId, onComplete, onError }: LoadingStateProps) {
  const [stage, setStage] = useState("queued");

  useEffect(() => {
    let mounted = true;

    const poll = async () => {
      try {
        const res = await getRepoStatus(repoId);
        if (!mounted) return;
        if (res.stage) setStage(res.stage);

        if (res.status === "ready") {
          onComplete();
        } else if (res.status === "error") {
          onError("Indexing failed. Please try again.");
        } else {
          setTimeout(poll, 1500);
        }
      } catch {
        if (mounted) setTimeout(poll, 2000);
      }
    };

    poll();
    return () => { mounted = false; };
  }, [repoId, onComplete, onError]);

  const currentIdx = STAGES.findIndex((s) => s.key === stage);
  const CurrentIcon = currentIdx >= 0 ? STAGES[currentIdx].Icon : GitBranch;

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-[#0a0a0a] px-6 py-20">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-[#111111] p-8 text-center shadow-xl shadow-black/30">
        <div className="relative mx-auto mb-7 w-fit">
          <div className="flex size-16 items-center justify-center rounded-2xl bg-zinc-800 text-zinc-100 shadow-lg shadow-black/30">
            <CurrentIcon className="size-7 animate-pulse" />
          </div>
          <div className="absolute -inset-2 rounded-3xl border-2 border-white/10 border-t-zinc-400 animate-spin" />
        </div>

        <p className="text-base font-semibold text-zinc-100">Indexing repository</p>
        <p className="mt-1 text-sm text-zinc-400">
          {STAGES.find((s) => s.key === stage)?.label || "Starting..."}
        </p>

        <div className="mt-7 space-y-2 text-left">
          {STAGES.map((s, i) => {
            const done = currentIdx > i;
            const active = currentIdx === i;

            return (
              <div
                key={s.key}
                className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors ${
                  active ? "bg-white/[0.06] text-zinc-100" : done ? "text-zinc-400" : "text-zinc-600"
                }`}
              >
                {done ? (
                  <CheckCircle2 className="size-4 shrink-0" />
                ) : (
                  <s.Icon className={`size-4 shrink-0 ${active ? "animate-spin" : ""}`} />
                )}
                <span>{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
