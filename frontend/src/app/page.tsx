"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import RepoInput from "@/components/RepoInput";
import { getIndexedRepos } from "@/lib/api";
import { getStoredRepo, type RepoMetadata } from "@/types";
import { GitFork, Star, ExternalLink } from "lucide-react";

export default function Home() {
  const [repos, setRepos] = useState<{ id: string; meta: RepoMetadata }[]>([]);
  const router = useRouter();

  useEffect(() => {
    const ids = getIndexedRepos();
    setRepos(ids.map((id) => ({ id, meta: getStoredRepo(id)! })).filter((r) => r.meta));
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0a0a0a] text-zinc-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(255,255,255,0.055),transparent_32%),linear-gradient(180deg,#101010_0%,#0a0a0a_52%,#050505_100%)]" />

      <header className="absolute inset-x-0 top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center px-6 py-5">
          <span className="text-sm font-semibold tracking-tight text-zinc-100">DeepWiki</span>
        </div>
      </header>

      <main className="relative z-0 grid min-h-screen place-items-center px-5 py-20">
        <section className="w-full max-w-2xl text-center">
          <div className="mx-auto mb-5 inline-flex items-center rounded-full border border-white/10 bg-white/[0.045] px-3 py-1 text-xs font-medium text-zinc-500 backdrop-blur">
            AI repo documentation
          </div>
          <h1 className="text-5xl font-semibold tracking-[-0.045em] text-white sm:text-6xl">
            DeepWiki
          </h1>
          <p className="mx-auto mt-4 max-w-md text-base leading-7 text-zinc-400">
            Paste a GitHub repository URL and generate a wiki you can read and ask questions about.
          </p>
          <div className="mx-auto mt-8 max-w-xl rounded-2xl border border-white/10 bg-[#111111]/90 p-2 shadow-2xl shadow-black/50 backdrop-blur">
            <RepoInput />
          </div>

          {repos.length > 0 && (
            <div className="mx-auto mt-16 max-w-2xl">
              <h2 className="mb-4 text-left text-sm font-semibold uppercase tracking-wider text-zinc-500">
                Recent repositories
              </h2>
              <div className="flex flex-col gap-3">
                {repos.map(({ id, meta }) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => router.push(`/repo/${id}`)}
                    className="group flex items-center gap-4 rounded-2xl border border-white/10 bg-[#111111]/80 p-4 text-left transition-colors hover:bg-[#1a1a1a]"
                  >
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <GitFork className="size-4 shrink-0 text-zinc-500" />
                        <span className="truncate text-sm font-semibold text-zinc-100">{meta.full_name}</span>
                      </div>
                      {meta.description && (
                        <p className="line-clamp-1 text-sm text-zinc-500">{meta.description}</p>
                      )}
                      <div className="flex items-center gap-3 text-xs text-zinc-600">
                        {meta.language && <span>{meta.language}</span>}
                        {meta.stars > 0 && (
                          <span className="flex items-center gap-1">
                            <Star className="size-3" />
                            {meta.stars}
                          </span>
                        )}
                      </div>
                    </div>
                    <ExternalLink className="size-4 shrink-0 text-zinc-600 opacity-0 transition-opacity group-hover:opacity-100" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
