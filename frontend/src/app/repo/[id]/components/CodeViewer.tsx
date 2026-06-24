"use client";

import { useState, useEffect } from "react";
import { X, FileCode, Copy, Check } from "lucide-react";

interface CodeViewerProps {
  filePath: string;
  content: string;
  startLine: number;
  onClose: () => void;
}

export default function CodeViewer({ filePath, content, startLine, onClose }: CodeViewerProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  const lines = content.split("\n");

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[85vh] w-[92vw] max-w-5xl flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#111111] shadow-2xl shadow-black/40">
        <div className="flex shrink-0 items-center justify-between border-b border-white/10 px-5 py-4">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-[#1a1a1a]">
              <FileCode className="size-4 text-zinc-400" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-zinc-100">{filePath}</p>
              <p className="text-xs text-zinc-500">line {startLine}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button type="button" onClick={handleCopy} className="rounded-xl p-2 text-zinc-500 transition-colors hover:bg-white/[0.08] hover:text-zinc-300" title="Copy">
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            </button>
            <button type="button" onClick={onClose} className="rounded-xl p-2 text-zinc-500 transition-colors hover:bg-white/[0.08] hover:text-zinc-300" title="Close">
              <X className="size-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto bg-slate-950">
          <table className="w-full border-collapse font-mono text-xs leading-relaxed">
            <tbody>
              {lines.map((line, i) => (
                <tr key={i} className="hover:bg-white/[0.04]">
                  <td className="w-0 select-none whitespace-nowrap border-r border-white/10 px-3 py-0 text-right align-top text-slate-500">
                    {startLine + i}
                  </td>
                  <td className="whitespace-pre px-4 py-0 text-slate-200">{line || " "}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
