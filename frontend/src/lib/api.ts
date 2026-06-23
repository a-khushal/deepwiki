const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function indexRepo(
  githubUrl: string
): Promise<{ repo_id: string; status: string; metadata: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/api/repo/index`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Failed to index repo");
  }
  return res.json();
}

export async function getRepoStatus(
  repoId: string
): Promise<{ status: string; progress?: number; stage?: string }> {
  const res = await fetch(`${API_BASE}/api/repo/${repoId}/status`);
  if (!res.ok) throw new Error("Failed to get status");
  return res.json();
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

export async function getDocs(
  repoId: string
): Promise<{ sections: { title: string; content: string }[] }> {
  const res = await fetch(`${API_BASE}/api/docs/${repoId}`);
  if (!res.ok) throw new Error("Failed to fetch docs");
  return res.json();
}
