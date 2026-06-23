import asyncio
import json
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.models.schemas import RepoDocs
from app.services.repo_service import RepoService
from app.services.rag_service import RagService
from app.services.vector_service import VectorService
from app.services.parser_service import ParserService
from app.services.doc_gen_service import DocGenService
from app.utils.entry_points import EntryPointDetector

logger = structlog.get_logger()
router = APIRouter(tags=["mcp"])

repo_service = RepoService()
rag_service = RagService()
vector_service = VectorService()
parser_service = ParserService()
doc_gen_service = DocGenService(vector_service=vector_service)
entry_detector = EntryPointDetector()

_sse_queues: dict[str, asyncio.Queue] = {}
_pending_requests: dict[str, asyncio.Future] = {}

TOOL_SCHEMAS = [
    {
        "name": "get_wiki_page",
        "description": "Get a specific wiki documentation page for a repository",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_id": {"type": "string", "description": "Repository ID (e.g. psf_requests)"},
                "page_title": {
                    "type": "string",
                    "description": "Page title: Overview, Getting Started, Module Breakdown, Key Components, or Architecture",
                },
            },
            "required": ["repo_id", "page_title"],
        },
    },
    {
        "name": "ask_question",
        "description": "Ask a natural language question about a repository's codebase",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_id": {"type": "string", "description": "Repository ID"},
                "question": {"type": "string", "description": "Your question about the codebase"},
            },
            "required": ["repo_id", "question"],
        },
    },
    {
        "name": "search_code",
        "description": "Semantically search for code in a repository",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_id": {"type": "string", "description": "Repository ID"},
                "query": {"type": "string", "description": "Search query describing what you're looking for"},
                "top_k": {"type": "number", "description": "Number of results (default 5)"},
            },
            "required": ["repo_id", "query"],
        },
    },
    {
        "name": "list_modules",
        "description": "List top-level modules and directories in a repository",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_id": {"type": "string", "description": "Repository ID"},
            },
            "required": ["repo_id"],
        },
    },
    {
        "name": "get_entry_points",
        "description": "Get the main entry points of a repository",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_id": {"type": "string", "description": "Repository ID"},
            },
            "required": ["repo_id"],
        },
    },
    {
        "name": "get_dependency_graph",
        "description": "Get module dependency relationships in a repository",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_id": {"type": "string", "description": "Repository ID"},
            },
            "required": ["repo_id"],
        },
    },
    {
        "name": "list_indexed_repos",
        "description": "List all indexed repositories",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _jsonrpc_error(id: str | None, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def _jsonrpc_result(id: str | None, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


async def _handle_tool_call(session_id: str, request_id: str, params: dict):
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    try:
        if tool_name == "get_wiki_page":
            result = await _tool_get_wiki_page(**arguments)
        elif tool_name == "ask_question":
            result = await _tool_ask_question(**arguments)
        elif tool_name == "search_code":
            result = await _tool_search_code(**arguments)
        elif tool_name == "list_modules":
            result = await _tool_list_modules(**arguments)
        elif tool_name == "get_entry_points":
            result = await _tool_get_entry_points(**arguments)
        elif tool_name == "get_dependency_graph":
            result = await _tool_get_dependency_graph(**arguments)
        elif tool_name == "list_indexed_repos":
            result = await _tool_list_indexed_repos()
        else:
            result = {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]}

        response = _jsonrpc_result(request_id, result)

    except Exception as e:
        logger.error("mcp_tool_error", tool=tool_name, error=str(e))
        response = _jsonrpc_error(request_id, -32603, str(e)[:200])

    _sse_queues[session_id].put_nowait(response)


async def _tool_get_wiki_page(repo_id: str, page_title: str) -> dict:
    if not repo_service.repo_exists(repo_id):
        return {"isError": True, "content": [{"type": "text", "text": f"Repository '{repo_id}' not found"}]}

    docs = doc_gen_service.get_docs(repo_id)
    if not docs:
        return {
            "isError": False,
            "content": [{"type": "text", "text": "No docs generated yet. Index the repo first via the web UI."}],
        }

    for section in docs.sections:
        if section.title.lower() == page_title.lower():
            return {
                "isError": False,
                "content": [
                    {"type": "text", "text": f"# {section.title}\n\n{section.content}"}
                ],
            }

    all_titles = [s.title for s in docs.sections]
    return {
        "isError": False,
        "content": [
            {
                "type": "text",
                "text": f"Page '{page_title}' not found. Available pages: {', '.join(all_titles)}",
            }
        ],
    }


async def _tool_ask_question(repo_id: str, question: str) -> dict:
    if not repo_service.repo_exists(repo_id):
        return {"isError": True, "content": [{"type": "text", "text": f"Repository '{repo_id}' not found"}]}

    if not vector_service.collection_exists(repo_id):
        return {
            "isError": False,
            "content": [{"type": "text", "text": "Repository not indexed yet. Index it first via the web UI."}],
        }

    result = rag_service.answer(repo_id, question)
    source_text = "\n\nSources:\n" + "\n".join(
        f"- {s['file_path']}:{s['start_line']}-{s['end_line']}" for s in result.sources
    ) if result.sources else ""

    return {
        "isError": False,
        "content": [{"type": "text", "text": result.answer + source_text}],
    }


async def _tool_search_code(repo_id: str, query: str, top_k: int = 5) -> dict:
    if not repo_service.repo_exists(repo_id):
        return {"isError": True, "content": [{"type": "text", "text": f"Repository '{repo_id}' not found"}]}

    from app.services.embedding_service import EmbeddingService

    emb = EmbeddingService()
    query_vec = emb.embed_query(query)
    results = vector_service.query(repo_id, query_vec, top_k=min(top_k, 20))

    if not results:
        return {"isError": False, "content": [{"type": "text", "text": "No results found."}]}

    parts = [f"Found {len(results)} results:\n"]
    for i, r in enumerate(results, 1):
        parts.append(
            f"### {i}. {r.chunk.file_path}:{r.chunk.start_line}-{r.chunk.end_line}\n"
            f"Symbol: {r.chunk.symbol_name or 'N/A'} ({r.chunk.symbol_type or 'N/A'})\n"
            f"Score: {r.score:.3f}\n"
            f"```\n{r.chunk.content[:300]}```\n"
        )

    return {"isError": False, "content": [{"type": "text", "text": "\n".join(parts)}]}


async def _tool_list_modules(repo_id: str) -> dict:
    repo_path = repo_service.get_repo_path(repo_id)
    if not repo_path.exists():
        return {"isError": True, "content": [{"type": "text", "text": f"Repository '{repo_id}' not found"}]}

    dirs = sorted(d.name for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith("."))
    files = sorted(f.name for f in repo_path.iterdir() if f.is_file() and not f.name.startswith("."))

    text = f"Repository: {repo_id}\n\n### Directories ({len(dirs)})\n"
    text += "\n".join(f"- {d}/" for d in dirs) if dirs else "(none)"
    text += f"\n\n### Files ({len(files)})\n"
    text += "\n".join(f"- {f}" for f in files) if files else "(none)"

    return {"isError": False, "content": [{"type": "text", "text": text}]}


async def _tool_get_entry_points(repo_id: str) -> dict:
    repo_path = repo_service.get_repo_path(repo_id)
    if not repo_path.exists():
        return {"isError": True, "content": [{"type": "text", "text": f"Repository '{repo_id}' not found"}]}

    entries = entry_detector.detect(str(repo_path))
    if not entries:
        return {"isError": False, "content": [{"type": "text", "text": "No entry points detected."}]}

    text = "### Entry Points (ranked)\n\n"
    for e in entries[:10]:
        desc = f" - {e.description}" if e.description else ""
        text += f"- [{e.rank}] `{e.file_path}` ({e.language}){desc}\n"

    return {"isError": False, "content": [{"type": "text", "text": text}]}


async def _tool_get_dependency_graph(repo_id: str) -> dict:
    repo_path = repo_service.get_repo_path(repo_id)
    if not repo_path.exists():
        return {"isError": True, "content": [{"type": "text", "text": f"Repository '{repo_id}' not found"}]}

    parsed = parser_service.parse_repo(str(repo_path))
    graph = parser_service.build_dependency_graph(parsed)

    text = f"### Dependency Graph\n\nTotal modules: {len(graph.nodes)}, Dependencies: {len(graph.edges)}\n\n"
    top = sorted(graph.edges, key=lambda e: len(e.imported_symbols), reverse=True)[:20]
    for e in top:
        src = e.source.split("/")[-1]
        tgt = e.target.split("/")[-1]
        text += f"- {src} → {tgt}\n"

    return {"isError": False, "content": [{"type": "text", "text": text}]}


async def _tool_list_indexed_repos() -> dict:
    import os
    from pathlib import Path

    repos_dir = Path("repos")
    if not repos_dir.exists():
        return {"isError": False, "content": [{"type": "text", "text": "No repositories indexed yet."}]}

    repodirs = sorted(d.name for d in repos_dir.iterdir() if d.is_dir())
    indexed = [r for r in repodirs if vector_service.collection_exists(r)]

    if not indexed:
        return {"isError": False, "content": [{"type": "text", "text": "No indexed repos found."}]}

    text = "### Indexed Repositories\n\n"
    for r in indexed:
        text += f"- {r}\n"

    return {"isError": False, "content": [{"type": "text", "text": text}]}


@router.get("/mcp/sse")
async def mcp_sse(request: Request):
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _sse_queues[session_id] = queue

    message_url = f"/mcp/message?session_id={session_id}"

    async def event_generator():
        try:
            yield f"event: endpoint\ndata: {message_url}\n\n"

            yield _sse_json({"jsonrpc": "2.0", "method": "tools/list", "params": {}})

            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield _sse_json(msg)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _sse_queues.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/mcp/message")
async def mcp_message(request: Request, session_id: str = ""):
    if not session_id or session_id not in _sse_queues:
        return _jsonrpc_error(None, -32000, "Invalid or missing session_id")

    try:
        body = await request.json()
    except Exception:
        return _jsonrpc_error(None, -32700, "Parse error")

    req_id = body.get("id", str(uuid.uuid4()))
    method = body.get("method", "")
    params = body.get("params", {})

    if method == "tools/list":
        response = _jsonrpc_result(req_id, {"tools": TOOL_SCHEMAS})
        _sse_queues[session_id].put_nowait(response)

    elif method == "tools/call":
        await _handle_tool_call(session_id, req_id, params)

    elif method == "initialize":
        response = _jsonrpc_result(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "DeepWiki MCP", "version": "0.1.0"},
        })
        _sse_queues[session_id].put_nowait(response)

    elif method == "ping":
        response = _jsonrpc_result(req_id, {})
        _sse_queues[session_id].put_nowait(response)

    else:
        response = _jsonrpc_error(req_id, -32601, f"Method not found: {method}")
        _sse_queues[session_id].put_nowait(response)

    return {"ok": True}


def _sse_json(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
