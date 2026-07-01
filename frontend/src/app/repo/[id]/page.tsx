"use client";

import { use, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getStoredRepo, type RepoMetadata } from "@/types";
import { getIndexedRepos } from "@/lib/api";
import LoadingState from "@/components/LoadingState";
import { Button } from "@/components/ui/button";
import DocsPanel from "./components/DocsPanel";
import ChatPanel from "./components/ChatPanel";
import CodeViewer from "./components/CodeViewer";
import FileTree from "./components/FileTree";
import { getFileContent } from "@/lib/api";
import { ArrowLeft, ExternalLink, GitFork, MessageCircle, X, FolderTree } from "lucide-react";

export default function RepoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeViewer, setCodeViewer] = useState<{
    filePath: string;
    content: string;
    startLine: number;
  } | null>(null);
  const [showMobileChat, setShowMobileChat] = useState(false);
  const [showFileTree, setShowFileTree] = useState(false);

  const [metadata, setMetadata] = useState<RepoMetadata | null>(null);

  useEffect(() => {
    if (getIndexedRepos().includes(id)) {
      setReady(true);
      setMetadata(getStoredRepo(id));
    }
  }, [id]);

  const handleComplete = useCallback(() => setReady(true), []);
  const handleError = useCallback(setError, []);

  const handleFileSelect = useCallback(async (filePath: string) => {
    try {
      const { content } = await getFileContent(id, filePath);
      setCodeViewer({ filePath, content, startLine: 1 });
    } catch {
      setError("Failed to load file");
    }
  }, [id]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 bg-[#0a0a0a]">
        <p className="text-sm text-zinc-400">{error}</p>
        <Button variant="outline" size="sm" onClick={() => router.push("/")}>
          Home
        </Button>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="flex flex-col">
        <header className="border-b border-white/10 bg-[#111111] px-6 py-3">
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-zinc-400 hover:text-zinc-100">
            <ArrowLeft className="size-4" />
            Back
          </Link>
        </header>
        <LoadingState repoId={id} onComplete={handleComplete} onError={handleError} />
      </div>
    );
  }

  return (
    <div className="flex h-dvh flex-col bg-[#0a0a0a] text-zinc-100">
      <header className="shrink-0 border-b border-white/10 bg-[#111111]/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1500px] items-center justify-between px-3 sm:px-6">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <Link href="/" className="shrink-0 text-sm font-semibold tracking-tight">DeepWiki</Link>
            <span className="hidden shrink-0 text-zinc-600 sm:inline">/</span>
            <div className="flex items-center gap-1.5 min-w-0">
              <GitFork className="hidden size-3.5 shrink-0 text-zinc-500 sm:block" />
              <span className="truncate text-sm font-medium text-zinc-300">{metadata?.full_name || id}</span>
              <a
                href={`https://github.com/${metadata?.full_name || id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 text-zinc-500 transition-colors hover:text-zinc-300"
              >
                <ExternalLink className="size-3" />
              </a>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowFileTree(!showFileTree)}
              className={`flex size-8 items-center justify-center rounded-xl border border-white/10 transition-colors ${
                showFileTree ? "bg-white/[0.10] text-zinc-200" : "bg-white/[0.05] text-zinc-400 hover:bg-white/[0.08]"
              }`}
              title="Toggle file tree"
            >
              <FolderTree className="size-4" />
            </button>
            <button
              type="button"
              onClick={() => setShowMobileChat(true)}
              className="flex size-8 items-center justify-center rounded-xl border border-white/10 bg-white/[0.05] text-zinc-400 lg:hidden"
            >
              <MessageCircle className="size-4" />
            </button>
            <Button variant="outline" size="sm" onClick={() => router.push("/")} className="rounded-full border-white/10 bg-white/[0.05] text-zinc-200 hover:bg-white/[0.10]">
              <ArrowLeft className="size-3.5 mr-1.5" />
              <span className="hidden sm:inline">New repo</span>
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex min-h-0 w-full max-w-[1500px] flex-1 gap-4 overflow-hidden p-3 sm:p-6">
        {showFileTree && (
          <div className="hidden w-[260px] shrink-0 overflow-hidden rounded-3xl border border-white/10 bg-[#111111] shadow-2xl shadow-black/20 lg:block">
            <div className="border-b border-white/10 px-4 py-2.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Files</span>
            </div>
            <FileTree repoId={id} onSelectFile={handleFileSelect} />
          </div>
        )}
        <div className="min-w-0 flex-1 overflow-hidden rounded-3xl border border-white/10 bg-[#111111] shadow-2xl shadow-black/20">
          <DocsPanel repoId={id} onViewSource={(fp, c, sl) => setCodeViewer({ filePath: fp, content: c, startLine: sl })} />
        </div>

        <aside className="hidden w-[390px] shrink-0 overflow-hidden rounded-3xl border border-white/10 bg-[#111111] shadow-2xl shadow-black/20 lg:flex lg:flex-col">
          <ChatPanel repoId={id} onViewSource={(fp, c, sl) => setCodeViewer({ filePath: fp, content: c, startLine: sl })} />
        </aside>
      </div>

      {/* Mobile chat overlay */}
      {showMobileChat && (
        <div className="fixed inset-0 z-40 flex flex-col bg-[#0a0a0a] lg:hidden">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <span className="text-sm font-semibold text-zinc-100">Chat</span>
            <button
              type="button"
              onClick={() => setShowMobileChat(false)}
              className="flex size-8 items-center justify-center rounded-xl text-zinc-400 hover:bg-white/[0.08]"
            >
              <X className="size-5" />
            </button>
          </div>
          <div className="flex-1 overflow-hidden">
            <ChatPanel repoId={id} onViewSource={(fp, c, sl) => setCodeViewer({ filePath: fp, content: c, startLine: sl })} />
          </div>
        </div>
      )}

      {codeViewer && (
        <CodeViewer
          filePath={codeViewer.filePath}
          content={codeViewer.content}
          startLine={codeViewer.startLine}
          onClose={() => setCodeViewer(null)}
        />
      )}
    </div>
  );
}
