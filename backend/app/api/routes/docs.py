from fastapi import APIRouter, HTTPException, Query
import structlog

from app.services.repo_service import RepoService
from app.services.parser_service import ParserService
from app.services.doc_gen_service import DocGenService
from app.services.vector_service import VectorService
from app.utils.entry_points import EntryPointDetector

logger = structlog.get_logger()
router = APIRouter(prefix="/api/docs", tags=["docs"])

repo_service = RepoService()
parser_service = ParserService()
doc_gen_service = DocGenService(vector_service=VectorService())
entry_detector = EntryPointDetector()
vector_service = VectorService()


@router.get("/{repo_id}")
async def get_docs(repo_id: str, regenerate: bool = Query(False)):
    if not repo_service.repo_exists(repo_id):
        raise HTTPException(status_code=404, detail="Repo not found")

    if not regenerate:
        cached = doc_gen_service.get_docs(repo_id)
        if cached:
            return {"sections": [s.model_dump() for s in cached.sections]}

    try:
        repo_path = repo_service.get_repo_path(repo_id)
        parsed = parser_service.parse_repo(str(repo_path))
        entries = entry_detector.detect(str(repo_path))
        dep_graph = parser_service.build_dependency_graph(parsed)

        parts = repo_id.split("_", 1)
        owner = parts[0] if len(parts) > 0 else ""
        repo_name_parts = parts[1] if len(parts) > 1 else ""

        docs = doc_gen_service.generate_docs(
            repo_id=repo_id,
            repo_name=f"{owner}/{repo_name_parts}" if repo_name_parts else repo_id,
            repo_path=str(repo_path),
            parsed_files=parsed,
            entry_points=entries,
            dep_graph=dep_graph,
        )

        return {"sections": [s.model_dump() for s in docs.sections]}

    except Exception as e:
        logger.error("docs_route_error", repo_id=repo_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e)[:200])
