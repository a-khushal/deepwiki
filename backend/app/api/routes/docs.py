from fastapi import APIRouter, HTTPException
import structlog

from app.services.repo_service import RepoService
from app.services.vector_service import VectorService

logger = structlog.get_logger()
router = APIRouter(prefix="/api/docs", tags=["docs"])

repo_service = RepoService()
vector_service = VectorService()


@router.get("/{repo_id}")
async def get_docs(repo_id: str):
    if not repo_service.repo_exists(repo_id):
        raise HTTPException(status_code=404, detail="Repo not found")

    return {
        "sections": [
            {
                "title": "Overview",
                "content": "Documentation will be generated in a future update. The repo has been indexed and is ready for Q&A.",
            }
        ]
    }
