"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { chat } from "@/lib/api";
import type { ChatMessage, SourceChunk, StreamEvent } from "@/types";
import { Send, Bot, User, FileCode, Loader2 } from "lucide-react";

const SUGGESTIONS = [
  "What is this project about?",
  "How do I get started?",
  "What are the main components?",
  "Show me the architecture",
];

interface ChatPanelProps {
  repoId: string;
  onViewSource: (filePath: string, content: string, startLine: number) => void;
}

export default function ChatPanel({ repoId, onViewSource }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (question: string) => {
    if (!question.trim() || streaming) return;
    setShowSuggestions(false);

    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: "user", content: question.trim() },
      { id: (Date.now() + 1).toString(), role: "assistant", content: "" },
    ]);
    setInput("");
    setStreaming(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const response = await chat(repoId, question, history);

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Chat failed" }));
        throw new Error((err as { detail?: string }).detail || "Chat failed");
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let buffer = "";
      let sources: SourceChunk[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event: StreamEvent = JSON.parse(line.slice(6));
            switch (event.type) {
              case "chunk":
                setMessages((prev) => {
                  const m = [...prev];
                  const last = m[m.length - 1];
                  if (last?.role === "assistant") last.content += event.content || "";
                  return m;
                });
                break;
              case "sources":
                sources = event.sources || [];
                break;
              case "done":
                setMessages((prev) => {
                  const m = [...prev];
                  const last = m[m.length - 1];
                  if (last?.role === "assistant" && sources.length > 0) last.sources = sources;
                  return m;
                });
                break;
              case "error":
                throw new Error(event.error || "Unknown error");
            }
          } catch (e) {
            if (e instanceof SyntaxError) continue;
            throw e;
          }
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Chat failed";
      setMessages((prev) => {
        const m = [...prev];
        const last = m[m.length - 1];
        if (last?.role === "assistant" && !last.content) last.content = `Error: ${message}`;
        return m;
      });
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex h-full flex-col bg-transparent text-zinc-100">
      <div className="shrink-0 border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-full bg-zinc-800 text-zinc-100">
            <Bot className="size-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-100">Ask DeepWiki</p>
            <p className="text-xs text-zinc-500">Answers grounded in retrieved code</p>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto bg-transparent px-4 py-5">
        {messages.length === 0 && showSuggestions && (
          <div className="space-y-3 rounded-2xl border border-white/10 bg-[#0a0a0a]/80 p-4 shadow-sm shadow-black/20">
            <p className="text-sm font-medium text-zinc-100">Start with a question</p>
            <div className="space-y-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => handleSend(s)}
                  className="block w-full rounded-xl border border-white/10 bg-[#0a0a0a] px-3 py-2 text-left text-sm text-zinc-400 transition-colors hover:border-white/20 hover:bg-white/[0.04] hover:text-zinc-100"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : ""}`}>
            {msg.role === "assistant" && (
              <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-[#1a1a1a] ring-1 ring-white/10">
                <Bot className="size-3.5 text-zinc-400" />
              </div>
            )}

            <div className={`max-w-[85%] space-y-1.5 ${msg.role === "user" ? "order-first" : ""}`}>
              {msg.role === "user" ? (
                <div className="rounded-2xl rounded-tr-sm bg-zinc-800 px-3.5 py-2 text-sm leading-6 text-zinc-100 shadow-sm">
                  {msg.content}
                </div>
              ) : (
                <div>
                  <div className="rounded-2xl rounded-tl-sm border border-white/10 bg-[#0d0d0d] px-3.5 py-2.5 text-sm leading-6 text-zinc-300 shadow-sm shadow-black/20">
                    {msg.content || (
                      <span className="italic text-zinc-500">
                        <Loader2 className="mr-1 inline size-3 animate-spin" />
                        Thinking...
                      </span>
                    )}
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-2">
                      {msg.sources.slice(0, 4).map((src, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => onViewSource(src.file_path, src.content, src.start_line)}
                          className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-[#0a0a0a] px-2 py-1 text-xs text-zinc-500 transition-colors hover:border-white/20 hover:text-zinc-300"
                        >
                          <FileCode className="size-3" />
                          {src.file_path.split("/").pop()}:{src.start_line}
                        </button>
                      ))}
                      {msg.sources.length > 4 && (
                        <span className="text-xs text-zinc-500">+{msg.sources.length - 4}</span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {msg.role === "user" && (
              <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-zinc-800">
                <User className="size-3.5 text-zinc-400" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="shrink-0 border-t border-white/10 bg-transparent p-3">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(input); }} className="flex gap-2">
          <Input
            ref={inputRef}
            type="text"
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={streaming}
            className="h-10 flex-1 rounded-xl border-white/10 bg-[#0a0a0a] text-sm text-zinc-100 placeholder:text-zinc-500 focus-visible:border-zinc-500 focus-visible:ring-0"
          />
          <Button type="submit" size="icon" disabled={!input.trim() || streaming} className="size-10 rounded-xl bg-zinc-100 text-zinc-950 hover:bg-white">
            {streaming ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          </Button>
        </form>
      </div>
    </div>
  );
}
