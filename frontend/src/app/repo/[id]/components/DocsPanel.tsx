"use client";

import { useEffect, useState } from "react";
import { getDocs } from "@/lib/api";
import type { DocSection } from "@/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";
import { Loader2, AlertCircle, FileText, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DocsPanelProps {
  repoId: string;
  onViewSource: (filePath: string, content: string, startLine: number) => void;
}

function MermaidDiagram({ code }: { code: string }) {
  const [Svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function render() {
      try {
        const mermaid = await import("mermaid");
        const id = `mermaid-${Math.random().toString(36).slice(2, 9)}`;
        const { svg } = await mermaid.default.render(id, code);
        if (mounted) setSvg(svg);
      } catch (e) {
        if (mounted) setError(e instanceof Error ? e.message : "Failed to render diagram");
      }
    }
    render();
    return () => { mounted = false; };
  }, [code]);

  if (error) {
    return (
      <div className="rounded-2xl border border-white/10 bg-[#0a0a0a] p-4 text-sm text-zinc-500">
        <pre className="mt-1 overflow-x-auto text-xs">{code}</pre>
      </div>
    );
  }

  if (!Svg) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-white/10 bg-[#0a0a0a] p-8">
        <Loader2 className="size-5 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div
      className="my-5 flex justify-center overflow-x-auto rounded-2xl border border-white/10 bg-[#111111] p-5 shadow-sm shadow-black/20"
      dangerouslySetInnerHTML={{ __html: Svg }}
    />
  );
}

function SectionRenderer({ section, isFirst }: { section: DocSection; isFirst: boolean }) {
  return (
    <section id={`s-${encodeURIComponent(section.title).toLowerCase()}`} className={isFirst ? "" : "mt-12 border-t border-white/10 pt-10"}>
      <div className="prose prose-invert prose-zinc max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeHighlight, rehypeRaw]}
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const lang = match ? match[1] : "";
              if (lang === "mermaid") {
                return <MermaidDiagram code={String(children).replace(/\n$/, "")} />;
              }
              return <code className={className} {...props}>{children}</code>;
            },
            pre({ children }) {
              return <>{children}</>;
            },
          }}
        >
          {section.content}
        </ReactMarkdown>
      </div>
    </section>
  );
}

export default function DocsPanel({ repoId }: DocsPanelProps) {
  const [sections, setSections] = useState<DocSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function fetch() {
      try {
        const docs = await getDocs(repoId);
        if (mounted) setSections(docs.sections);
      } catch (e) {
        if (mounted) setError(e instanceof Error ? e.message : "Failed to load docs");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetch();
    return () => { mounted = false; };
  }, [repoId]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="size-5 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <AlertCircle className="size-6 text-zinc-500" />
        <p className="text-sm text-zinc-500">{error}</p>
        <Button variant="outline" size="sm" onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  if (sections.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <FileText className="size-6 text-zinc-500" />
        <p className="text-sm text-zinc-500">No documentation yet.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-transparent text-zinc-100">
      <nav className="hidden w-56 shrink-0 overflow-y-auto border-r border-white/10 bg-[#0a0a0a]/70 md:block">
        <div className="p-4">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            <BookOpen className="size-3.5" />
            Pages
          </div>
          <div className="space-y-1">
            {sections.map((s) => (
              <a
                key={s.title}
                href={`#s-${encodeURIComponent(s.title).toLowerCase()}`}
                className="block rounded-xl px-3 py-2 text-sm font-medium text-zinc-500 transition-colors hover:bg-white/[0.05] hover:text-zinc-100"
              >
                {s.title}
              </a>
            ))}
          </div>
        </div>
      </nav>

      <div className="flex-1 overflow-y-auto bg-transparent">
        <div className="mx-auto max-w-3xl px-6 py-10 pb-32 sm:px-10">
          <div className="mb-8 rounded-2xl border border-white/10 bg-[#0d0d0d] p-5 shadow-sm shadow-black/20">
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Generated wiki</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-zinc-100">Repository Documentation</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-400">Architecture, setup notes, components, and generated code explanations.</p>
          </div>
          {sections.map((s, i) => (
            <SectionRenderer key={s.title} section={s} isFirst={i === 0} />
          ))}
        </div>
      </div>
    </div>
  );
}
