"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { indexRepo } from "@/lib/api";
import { storeRepo } from "@/types";
import { ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

const GITHUB_URL_RE = /^https?:\/\/github\.com\/([\w.-]+)\/([\w.-]+)\/?$/;

function normalizeUrl(url: string): string {
  const trimmed = url.trim().replace(/\/+$/, "");
  if (/^https?:\/\//.test(trimmed)) return trimmed;
  if (trimmed.startsWith("github.com")) return `https://${trimmed}`;
  if (trimmed.startsWith("/")) return `https://github.com${trimmed}`;
  if (trimmed.includes("/")) return `https://github.com/${trimmed}`;
  return trimmed;
}

export default function RepoInput() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalized = normalizeUrl(url);
    const match = normalized.match(GITHUB_URL_RE);
    if (!match) {
      toast.error("Invalid GitHub URL", {
        description: "Use format: https://github.com/owner/repo",
      });
      return;
    }

    setLoading(true);
    try {
      const result = await indexRepo(normalized);
      storeRepo(result.repo_id, result.metadata);
      toast.success("Indexing started", {
        description: result.metadata.full_name,
      });
      router.push(`/repo/${result.repo_id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to index repo";
      toast.error("Indexing failed", { description: message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row">
      <input
        type="text"
        placeholder="https://github.com/owner/repo"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        disabled={loading}
        className="h-12 flex-1 rounded-xl border border-white/10 bg-[#0a0a0a] px-4 text-sm text-zinc-100 placeholder:text-zinc-600 transition-colors focus:border-zinc-500 focus:bg-[#0f0f0f] focus:outline-none disabled:opacity-50"
      />
      <Button
        type="submit"
        disabled={loading || !url.trim()}
        className="h-12 rounded-xl bg-zinc-100 px-5 text-sm font-medium text-zinc-950 hover:bg-white disabled:bg-zinc-800 disabled:text-zinc-500 sm:min-w-36"
      >
        {loading ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <>
            Explore
            <ArrowRight className="size-4" />
          </>
        )}
      </Button>
    </form>
  );
}
