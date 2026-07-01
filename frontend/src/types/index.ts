export interface RepoMetadata {
  name: string;
  full_name: string;
  description: string;
  language: string;
  topics: string[];
  stars: number;
  default_branch: string;
  owner: string;
}

export interface IndexResponse {
  repo_id: string;
  status: string;
  metadata: RepoMetadata;
}

export interface RepoStatus {
  status: string;
  progress?: number;
  stage?: string;
}

export interface DocSection {
  title: string;
  content: string;
}

export interface SourceChunk {
  file_path: string;
  content: string;
  start_line: number;
  end_line: number;
  symbol_name?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
}

export interface StreamEvent {
  type: "chunk" | "sources" | "done" | "error";
  content?: string;
  sources?: SourceChunk[];
  error?: string;
}

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children?: FileNode[];
}

export interface ExampleRepo {
  url: string;
  label: string;
  description: string;
}

export function getStoredRepo(repoId: string): RepoMetadata | null {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem(`repo:${repoId}`);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as RepoMetadata;
  } catch {
    return null;
  }
}

export function storeRepo(repoId: string, metadata: RepoMetadata): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(`repo:${repoId}`, JSON.stringify(metadata));
}
