from app.models.schemas import RepoStatus


class IndexingService:
    def __init__(self):
        self._status: dict[str, RepoStatus] = {}
        self._stages: dict[str, str] = {}
        self._progress: dict[str, float] = {}

    def set(self, repo_id: str, status: RepoStatus, stage: str = "", progress: float = 0.0):
        self._status[repo_id] = status
        self._stages[repo_id] = stage
        self._progress[repo_id] = progress

    def get(self, repo_id: str) -> dict:
        return {
            "repo_id": repo_id,
            "status": self._status.get(repo_id, RepoStatus.error).value,
            "stage": self._stages.get(repo_id, ""),
            "progress": self._progress.get(repo_id, 0.0),
        }

    def remove(self, repo_id: str):
        self._status.pop(repo_id, None)
        self._stages.pop(repo_id, None)
        self._progress.pop(repo_id, None)


indexing_service = IndexingService()
