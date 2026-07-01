"use client";

import { useState, useEffect } from "react";
import { getRepoFiles } from "@/lib/api";
import type { FileNode } from "@/types";
import { ChevronRight, ChevronDown, File, Folder, FolderOpen, Loader2 } from "lucide-react";

interface FileTreeProps {
  repoId: string;
  onSelectFile: (filePath: string) => void;
  highlightedFiles?: string[];
}

function TreeNode({
  node,
  depth,
  onSelect,
  highlighted,
}: {
  node: FileNode;
  depth: number;
  onSelect: (path: string) => void;
  highlighted: boolean;
}) {
  const [open, setOpen] = useState(depth < 1);

  if (node.type === "dir") {
    return (
      <div>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1 text-left text-sm text-zinc-400 transition-colors hover:bg-white/[0.04] hover:text-zinc-200"
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          {open ? <ChevronDown className="size-3.5 shrink-0" /> : <ChevronRight className="size-3.5 shrink-0" />}
          {open ? <FolderOpen className="size-4 shrink-0 text-zinc-500" /> : <Folder className="size-4 shrink-0 text-zinc-500" />}
          <span className="truncate">{node.name}</span>
        </button>
        {open && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeNode
                key={child.path}
                node={child}
                depth={depth + 1}
                onSelect={onSelect}
                highlighted={highlighted ? highlighted : false}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onSelect(node.path)}
      className={`flex w-full items-center gap-1.5 rounded-lg px-2 py-1 text-left text-sm transition-colors ${
        highlighted
          ? "bg-white/[0.08] text-zinc-100"
          : "text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-300"
      }`}
      style={{ paddingLeft: `${depth * 16 + 28}px` }}
    >
      <File className="size-4 shrink-0 text-zinc-600" />
      <span className="truncate">{node.name}</span>
    </button>
  );
}

export default function FileTree({ repoId, onSelectFile, highlightedFiles }: FileTreeProps) {
  const [tree, setTree] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getRepoFiles(repoId).then((data) => {
      if (mounted) {
        setTree(data);
        setLoading(false);
      }
    }).catch(() => {
      if (mounted) setLoading(false);
    });
    return () => { mounted = false; };
  }, [repoId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="size-4 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (tree.length === 0) {
    return <p className="px-3 py-4 text-sm text-zinc-500">No source files found.</p>;
  }

  return (
    <div className="overflow-y-auto py-2">
      {tree.map((node) => (
        <TreeNode
          key={node.path}
          node={node}
          depth={0}
          onSelect={onSelectFile}
          highlighted={highlightedFiles?.some((h) => h === node.path || node.path.startsWith(h.replace("*", ""))) ?? false}
        />
      ))}
    </div>
  );
}
