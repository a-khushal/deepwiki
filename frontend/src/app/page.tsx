"use client";

import RepoInput from "@/components/RepoInput";

export default function Home() {
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
        </section>
      </main>
    </div>
  );
}
