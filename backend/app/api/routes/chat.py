import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import structlog

from app.models.schemas import ChatRequest
from app.services.rag_service import RagService
from app.services.vector_service import VectorService
from app.services.repo_service import RepoService

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["chat"])

rag_service = RagService()
vector_service = VectorService()
repo_service = RepoService()


@router.post("/chat")
async def chat(body: ChatRequest):
    if not repo_service.repo_exists(body.repo_id):
        raise HTTPException(status_code=404, detail="Repo not found")

    if not vector_service.collection_exists(body.repo_id):
        raise HTTPException(status_code=400, detail="Repo not indexed yet")

    async def event_stream():
        try:
            async for chunk in rag_service.answer_stream(body.repo_id, body.question, body.history):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            logger.error("chat_stream_error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/sync")
async def chat_sync(body: ChatRequest):
    if not repo_service.repo_exists(body.repo_id):
        raise HTTPException(status_code=404, detail="Repo not found")

    if not vector_service.collection_exists(body.repo_id):
        raise HTTPException(status_code=400, detail="Repo not indexed yet")

    try:
        result = rag_service.answer(body.repo_id, body.question, body.history)
        return {"answer": result.answer, "sources": result.sources}
    except Exception as e:
        logger.error("chat_sync_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
