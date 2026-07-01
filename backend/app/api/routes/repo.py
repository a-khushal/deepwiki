from fastapi import APIRouter, BackgroundTasks, HTTPException
import structlog

from app.models.schemas import IndexRequest, RepoMetadata, RepoStatus
from app.services.repo_service import RepoService
from app.services.parser_service import ParserService
from app.services.chunker_service import ChunkerService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.services.indexing_service import indexing_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/repo", tags=["repo"])

repo_service = RepoService()
parser_service = ParserService()
chunker_service = ChunkerService()
embedding_service = EmbeddingService()
vector_service = VectorService()


@router.post("/index")
async def index_repo(body: IndexRequest, background_tasks: BackgroundTasks):
    if not repo_service.validate_github_url(body.github_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    try:
        meta = repo_service.clone_repo(body.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if meta.status == RepoStatus.ready and vector_service.collection_exists(meta.repo_id):
        return {
            "repo_id": meta.repo_id,
            "status": "ready",
            "metadata": meta.model_dump(),
        }

    background_tasks.add_task(_index_pipeline, meta.repo_id)
    return {
        "repo_id": meta.repo_id,
        "status": "indexing",
        "metadata": meta.model_dump(),
    }


@router.get("/{repo_id}/status")
async def get_status(repo_id: str):
    if not repo_service.repo_exists(repo_id):
        raise HTTPException(status_code=404, detail="Repo not found")
    return indexing_service.get(repo_id)


@router.get("/{repo_id}/files")
async def get_repo_files(repo_id: str):
    if not repo_service.repo_exists(repo_id):
        raise HTTPException(status_code=404, detail="Repo not found")
    return repo_service.get_file_tree(repo_id)


@router.get("/{repo_id}/file")
async def get_repo_file(repo_id: str, path: str):
    if not repo_service.repo_exists(repo_id):
        raise HTTPException(status_code=404, detail="Repo not found")
    repo_path = repo_service.get_repo_path(repo_id)
    file_path = repo_path / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = file_path.read_text("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read file")
    return {"path": path, "content": content}


@router.delete("/{repo_id}")
async def delete_repo(repo_id: str):
    repo_service.delete_repo(repo_id)
    vector_service.delete_collection(repo_id)
    indexing_service.remove(repo_id)
    return {"status": "deleted"}


def _index_pipeline(repo_id: str):
    try:
        indexing_service.set(repo_id, RepoStatus.indexing, "Parsing code", 0.2)
        repo_path = repo_service.get_repo_path(repo_id)
        parsed = parser_service.parse_repo(str(repo_path))
        logger.info("pipeline_parse_done", repo_id=repo_id, files=len(parsed))

        indexing_service.set(repo_id, RepoStatus.indexing, "Chunking code", 0.4)
        chunks = chunker_service.chunk_parsed_files(parsed, repo_id)
        logger.info("pipeline_chunk_done", repo_id=repo_id, chunks=len(chunks))

        indexing_service.set(repo_id, RepoStatus.indexing, "Generating embeddings", 0.6)
        texts = [c.content for c in chunks]
        embeddings = embedding_service.embed(texts)
        logger.info("pipeline_embed_done", repo_id=repo_id, count=len(embeddings))

        indexing_service.set(repo_id, RepoStatus.indexing, "Storing in vector DB", 0.8)
        vector_service.store_chunks(repo_id, chunks, embeddings)

        indexing_service.set(repo_id, RepoStatus.ready, "Ready", 1.0)
        logger.info("pipeline_complete", repo_id=repo_id)

    except Exception as e:
        logger.error("pipeline_failed", repo_id=repo_id, error=str(e))
        indexing_service.set(repo_id, RepoStatus.error, f"Failed: {str(e)[:100]}", 0.0)
