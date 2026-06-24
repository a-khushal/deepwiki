import type { IndexResponse, RepoStatus, DocSection } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function indexRepo(githubUrl: string): Promise<IndexResponse> {
  const res = await fetch(`${API_BASE}/api/repo/index`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl }),
  });
  return handleResponse<IndexResponse>(res);
}

export async function getRepoStatus(repoId: string): Promise<RepoStatus> {
  const res = await fetch(`${API_BASE}/api/repo/${repoId}/status`);
  return handleResponse<RepoStatus>(res);
}

export async function deleteRepo(repoId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/repo/${repoId}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail || "Failed to delete repo");
  }
}

export async function chat(
  repoId: string,
  question: string,
  history?: { role: string; content: string }[]
): Promise<Response> {
  return fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_id: repoId, question, history: history || [] }),
  });
}

export async function getDocs(repoId: string, regenerate?: boolean): Promise<{ sections: DocSection[] }> {
  const url = regenerate
    ? `${API_BASE}/api/docs/${repoId}?regenerate=true`
    : `${API_BASE}/api/docs/${repoId}`;
  const res = await fetch(url);
  return handleResponse<{ sections: DocSection[] }>(res);
}

export function getIndexedRepos(): string[] {
  if (typeof window === "undefined") return [];
  const keys: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith("repo:")) {
      keys.push(key.slice(5));
    }
  }
  return keys;
}
