import json
import structlog

from openai import OpenAI

from app.config import settings
from app.models.schemas import RepoDocs, DocSection, EntryPoint, DependencyGraph, ParsedFile
from app.utils.file_utils import LANGUAGE_MAP

logger = structlog.get_logger()

DOC_GEN_PROMPT = """You are an expert technical writer generating documentation for a GitHub repository.

Repository: {repo_name}
Description: {description}

## Entry Points
{entry_points}

## Directory Structure
{dir_structure}

## Key Files & Symbols
{key_symbols}

## Dependency Graph Summary
{dep_summary}

Based on the above information, generate documentation for this repository with the following 5 sections.

Return your response as valid JSON with this exact structure:
{{
  "sections": [
    {{"title": "Overview", "content": "markdown content..."}},
    {{"title": "Getting Started", "content": "markdown content..."}},
    {{"title": "Module Breakdown", "content": "markdown content..."}},
    {{"title": "Key Components", "content": "markdown content..."}},
    {{"title": "Architecture", "content": "markdown content..."}}
  ]
}}

## Rules
- Use valid markdown in content (headings, lists, code blocks, bold)
- You MUST include a mermaid code block in the Architecture section showing the module dependency flow, for example:
  ```mermaid
  graph TD
      n1["main.py"]
      n2["utils/helpers.py"]
      n1 --> n2
  ```
- Be accurate and specific — reference actual file paths and symbols
- Keep Overview to 2-3 paragraphs
- Keep each section under 500 words
- Output ONLY the JSON object, no other text"""


class DocGenService:
    def __init__(self, vector_service=None):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model
        self._vector_service = vector_service

    def _get_docs_collection_name(self, repo_id: str) -> str:
        return f"{repo_id}_docs"

    def generate_docs(
        self,
        repo_id: str,
        repo_name: str,
        repo_path: str,
        parsed_files: list[ParsedFile],
        entry_points: list[EntryPoint],
        dep_graph: DependencyGraph,
    ) -> RepoDocs:
        cached = self._get_cached_docs(repo_id)
        if cached:
            logger.info("docs_cache_hit", repo_id=repo_id)
            return cached

        logger.info("generating_docs", repo_id=repo_id)
        dir_structure = self._build_dir_structure(repo_path)
        key_symbols = self._build_key_symbols(parsed_files)
        entry_text = self._format_entry_points(entry_points)
        dep_summary = self._format_dep_graph(dep_graph, parsed_files)

        prompt = DOC_GEN_PROMPT.format(
            repo_name=repo_name,
            description=self._generate_description(repo_name, entry_points, parsed_files),
            entry_points=entry_text,
            dir_structure=dir_structure,
            key_symbols=key_symbols,
            dep_summary=dep_summary,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical documentation generator. Output only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or ""
            data = json.loads(content)
            sections = [DocSection(**s) for s in data.get("sections", [])]

            dep_diagram = self._generate_dep_diagram(dep_graph)
            if dep_diagram:
                for s in sections:
                    if s.title.lower() == "architecture":
                        s.content += f"\n\n### Dependency Graph\n\n{dep_diagram}\n"
                        break

            docs = RepoDocs(repo_id=repo_id, sections=sections)
            self._cache_docs(repo_id, docs)
            return docs

        except Exception as e:
            logger.error("docs_generation_failed", error=str(e))
            return RepoDocs(
                repo_id=repo_id,
                sections=[
                    DocSection(
                        title="Overview",
                        content=f"Repository: **{repo_name}**\n\nDocumentation generation failed. The repository has been indexed and is ready for Q&A via the chat interface.",
                    )
                ],
            )

    def _get_cached_docs(self, repo_id: str) -> RepoDocs | None:
        if not self._vector_service:
            return None

        collection_name = self._get_docs_collection_name(repo_id)

        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(
                path=settings.chroma_dir,
                settings=Settings(anonymized_telemetry=False),
            )

            try:
                collection = client.get_collection(collection_name)
            except ValueError:
                return None

            results = collection.get()
            if not results["documents"]:
                return None

            for doc in results["documents"]:
                try:
                    data = json.loads(doc)
                    sections = [DocSection(**s) for s in data.get("sections", [])]
                    return RepoDocs(repo_id=repo_id, sections=sections)
                except (json.JSONDecodeError, KeyError):
                    continue

            return None

        except Exception as e:
            logger.warning("docs_cache_read_failed", error=str(e))
            return None

    def _cache_docs(self, repo_id: str, docs: RepoDocs):
        if not self._vector_service:
            return

        collection_name = self._get_docs_collection_name(repo_id)

        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(
                path=settings.chroma_dir,
                settings=Settings(anonymized_telemetry=False),
            )

            try:
                client.delete_collection(collection_name)
            except ValueError:
                pass

            collection = client.create_collection(collection_name)

            doc_json = json.dumps({"sections": [s.model_dump() for s in docs.sections]})

            collection.add(
                ids=[repo_id],
                documents=[doc_json],
                metadatas=[{"type": "repo_docs", "repo_id": repo_id}],
            )

            logger.info("docs_cached", repo_id=repo_id, sections=len(docs.sections))

        except Exception as e:
            logger.warning("docs_cache_write_failed", error=str(e))

    def _generate_dep_diagram(self, dep_graph: DependencyGraph) -> str:
        if not dep_graph.edges:
            return ""

        lines = ["```mermaid", "graph TD"]
        node_ids: dict[str, str] = {}
        counter = 1

        def label(p: str) -> str:
            parts = p.split("/")
            if len(parts) >= 3:
                return f".../{parts[-2]}/{parts[-1]}"
            return p

        for e in dep_graph.edges[:20]:
            for p in (e.source, e.target):
                if p not in node_ids:
                    node_ids[p] = f"n{counter}"
                    lines.append(f'    {node_ids[p]}["{label(p)}"]')
                    counter += 1

        for e in dep_graph.edges[:20]:
            lines.append(f"    {node_ids[e.source]} --> {node_ids[e.target]}")

        lines.append("```")
        return "\n".join(lines)

    def _build_dir_structure(self, repo_path: str) -> str:
        import os
        from pathlib import Path

        root = Path(repo_path)
        lines = []
        skip_dirs = {"__pycache__", ".git", "node_modules", ".venv", "__pycache__", ".next", "build", "dist"}

        for path in sorted(root.rglob("*")):
            if any(p in skip_dirs for p in path.parts):
                continue
            if path.is_file():
                rel = path.relative_to(root)
                ext = path.suffix.lower()
                if ext in LANGUAGE_MAP:
                    lines.append(f"  {rel}")

        if len(lines) > 60:
            lines = lines[:60]
            lines.append("  ... (and more files)")

        return "\n".join(lines) if lines else "  (no source files detected)"

    def _build_key_symbols(self, parsed_files: list[ParsedFile]) -> str:
        symbols_by_file: dict[str, list[str]] = {}
        for pf in parsed_files:
            file_key = pf.file_path.split("/")[-1] if "/" in pf.file_path else pf.file_path
            names = [s for s in pf.symbols if s.type in ("function", "class", "method")]
            if names:
                symbols_by_file[file_key] = [f"{s.type}: {s.name}" for s in names[:10]]

        lines = []
        count = 0
        for file_name, syms in sorted(symbols_by_file.items())[:30]:
            lines.append(f"  {file_name}: {', '.join(syms[:5])}")
            count += 1
            if count >= 30:
                break

        return "\n".join(lines) if lines else "  (no symbols extracted)"

    def _format_entry_points(self, entry_points: list[EntryPoint]) -> str:
        if not entry_points:
            return "  (none detected)"
        return "\n".join(
            f"  [{e.rank}] {e.file_path} ({e.language}){' - ' + e.description if e.description else ''}"
            for e in entry_points[:5]
        )

    def _format_dep_graph(self, dep_graph: DependencyGraph, parsed_files: list[ParsedFile]) -> str:
        if not dep_graph.edges:
            return "  (no dependencies detected)"

        top_edges = sorted(dep_graph.edges, key=lambda e: len(e.imported_symbols), reverse=True)[:15]
        edge_lines = []
        for e in top_edges:
            source_short = e.source.split("/")[-1]
            target_short = e.target.split("/")[-1]
            edge_lines.append(f"  {source_short} → {target_short}")

        "\n".join(edge_lines)
        return f"  Total modules: {len(dep_graph.nodes)}, Dependencies: {len(dep_graph.edges)}\n" + "\n".join(edge_lines)

    def _generate_description(
        self, repo_name: str, entry_points: list[EntryPoint], parsed_files: list[ParsedFile]
    ) -> str:
        languages = set(pf.language for pf in parsed_files)
        lang_str = ", ".join(sorted(languages)[:5]) if languages else "unknown"
        file_count = len(parsed_files)

        entry_hint = ""
        if entry_points:
            entry_hint = f" Entry points include {entry_points[0].file_path}."

        return f"A {lang_str} repository with {file_count} source files.{entry_hint}"

    def get_docs(self, repo_id: str) -> RepoDocs | None:
        return self._get_cached_docs(repo_id)
