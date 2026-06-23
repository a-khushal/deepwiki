from pydantic import BaseModel
from typing import Optional
from enum import Enum


class RepoStatus(str, Enum):
    cloning = "cloning"
    indexing = "indexing"
    ready = "ready"
    error = "error"


class RepoMetadata(BaseModel):
    repo_id: str
    name: str
    owner: str
    default_branch: str
    file_count: int
    languages: list[str]
    total_chunks: Optional[int] = None
    status: RepoStatus = RepoStatus.ready


class RepoStatusResponse(BaseModel):
    repo_id: str
    status: RepoStatus
    stage: Optional[str] = None
    progress: Optional[float] = None


class IndexRequest(BaseModel):
    github_url: str


class CodeSymbol(BaseModel):
    name: str
    type: str  # function | class | method | import
    code: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    docstring: Optional[str] = None


class ParsedFile(BaseModel):
    file_path: str
    language: str
    symbols: list[CodeSymbol]


class EntryPoint(BaseModel):
    file_path: str
    language: str
    rank: int
    description: Optional[str] = None


class DependencyNode(BaseModel):
    file_path: str
    exports: list[str] = []


class DependencyEdge(BaseModel):
    source: str
    target: str
    imported_symbols: list[str] = []


class DependencyGraph(BaseModel):
    nodes: list[DependencyNode] = []
    edges: list[DependencyEdge] = []


class CodeChunk(BaseModel):
    repo_id: str
    file_path: str
    language: str
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    start_line: int
    end_line: int
    chunk_index: int = 0
    content: str


class SearchResult(BaseModel):
    chunk: CodeChunk
    score: float


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    repo_id: str
    question: str
    history: list[Message] = []


class RagResponse(BaseModel):
    answer: str
    sources: list[dict] = []


class DocSection(BaseModel):
    title: str
    content: str


class RepoDocs(BaseModel):
    repo_id: str
    sections: list[DocSection] = []
