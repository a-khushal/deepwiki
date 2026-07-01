import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from app.utils.file_utils import should_include, INCLUDE_EXTENSIONS, EXCLUDE_DIRS, EXCLUDE_FILES, MAX_FILE_SIZE

import git
import structlog

from app.config import settings
from app.models.schemas import RepoMetadata, RepoStatus

logger = structlog.get_logger()

MAX_REPO_SIZE_MB = 100


class RepoService:
    def __init__(self):
        self.repos_dir = Path(settings.repos_dir)
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self._status: dict[str, RepoStatus] = {}
        self._stages: dict[str, str] = {}
        self._progress: dict[str, float] = {}

    def validate_github_url(self, url: str) -> bool:
        pattern = r"^https?://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+/?$"
        if not re.match(pattern, url.strip()):
            return False
        return True

    def _parse_github_url(self, url: str) -> tuple[str, str, str]:
        path = urlparse(url.strip()).path.strip("/")
        parts = path.split("/")
        owner, repo_name = parts[0], parts[1]
        repo_name = repo_name.replace(".git", "")
        repo_id = f"{owner}_{repo_name}"
        return owner, repo_name, repo_id

    def _get_repo_path(self, repo_id: str) -> Path:
        return self.repos_dir / repo_id

    def _check_repo_size(self, url: str) -> bool:
        import httpx
        try:
            resp = httpx.head(url, follow_redirects=True, timeout=10)
            size = resp.headers.get("content-length")
            if size and int(size) > MAX_REPO_SIZE_MB * 1024 * 1024:
                return False
        except Exception:
            pass
        return True

    def _estimate_local_size(self, repo_path: Path) -> int:
        total = 0
        for f in repo_path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
        return total

    def clone_repo(self, url: str) -> RepoMetadata:
        if not self.validate_github_url(url):
            raise ValueError(f"Invalid GitHub URL: {url}")

        if not self._check_repo_size(url):
            raise ValueError(f"Repo exceeds {MAX_REPO_SIZE_MB}MB limit")

        owner, repo_name, repo_id = self._parse_github_url(url)
        repo_path = self._get_repo_path(repo_id)

        self._set_status(repo_id, RepoStatus.cloning, "Cloning repository", 0.0)

        if repo_path.exists():
            logger.info("repo_already_cloned", repo_id=repo_id)
            self._set_status(repo_id, RepoStatus.ready, "Already cloned", 1.0)
            return self._build_metadata(repo_path, owner, repo_name, repo_id)

        try:
            logger.info("cloning_repo", url=url, repo_id=repo_id)
            repo = git.Repo.clone_from(url, str(repo_path), depth=1)
            self._set_status(repo_id, RepoStatus.ready, "Cloned", 1.0)

            default_branch = repo.active_branch.name if not repo.head.is_detached else "HEAD"

            languages = self._detect_languages(repo_path)
            file_count = sum(1 for _ in repo_path.rglob("*") if _.is_file())

            return RepoMetadata(
                repo_id=repo_id,
                name=repo_name,
                owner=owner,
                default_branch=default_branch,
                file_count=file_count,
                languages=languages,
            )
        except git.exc.GitCommandError as e:
            self._set_status(repo_id, RepoStatus.error, f"Clone failed: {e}", 0.0)
            if "Authentication failed" in str(e) or "Repository not found" in str(e):
                raise ValueError(f"Private repo or access denied: {url}")
            raise ValueError(f"Failed to clone repo: {e}")

    def _build_metadata(
        self, repo_path: Path, owner: str, repo_name: str, repo_id: str
    ) -> RepoMetadata:
        try:
            repo = git.Repo(str(repo_path))
            default_branch = repo.active_branch.name if not repo.head.is_detached else "HEAD"
        except Exception:
            default_branch = "main"

        languages = self._detect_languages(repo_path)
        file_count = sum(1 for _ in repo_path.rglob("*") if _.is_file())

        return RepoMetadata(
            repo_id=repo_id,
            name=repo_name,
            owner=owner,
            default_branch=default_branch,
            file_count=file_count,
            languages=languages,
        )

    def _detect_languages(self, repo_path: Path) -> list[str]:
        extensions = set()
        for f in repo_path.rglob("*"):
            if f.is_file() and "." in f.name:
                ext = f.name.rsplit(".", 1)[1].lower()
                extensions.add(ext)
        lang_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "jsx": "javascript",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "cpp": "cpp",
            "c": "c",
            "rb": "ruby",
            "php": "php",
            "md": "markdown",
            "yaml": "yaml",
            "yml": "yaml",
            "json": "json",
            "toml": "toml",
        }
        return sorted({lang_map[e] for e in extensions if e in lang_map})

    def get_repo_status(self, repo_id: str) -> RepoStatus:
        return self._status.get(repo_id, RepoStatus.error)

    def get_status_detail(self, repo_id: str) -> dict:
        return {
            "repo_id": repo_id,
            "status": self._status.get(repo_id, RepoStatus.error).value,
            "stage": self._stages.get(repo_id, ""),
            "progress": self._progress.get(repo_id, 0.0),
        }

    def _set_status(self, repo_id: str, status: RepoStatus, stage: str, progress: float):
        self._status[repo_id] = status
        self._stages[repo_id] = stage
        self._progress[repo_id] = progress

    def repo_exists(self, repo_id: str) -> bool:
        return self._get_repo_path(repo_id).exists()

    def delete_repo(self, repo_id: str):
        repo_path = self._get_repo_path(repo_id)
        if repo_path.exists():
            shutil.rmtree(repo_path)
            logger.info("deleted_repo", repo_id=repo_id)
        self._status.pop(repo_id, None)
        self._stages.pop(repo_id, None)
        self._progress.pop(repo_id, None)

    def get_repo_path(self, repo_id: str) -> Path:
        return self._get_repo_path(repo_id)

    def get_file_tree(self, repo_id: str) -> list[dict]:
        repo_path = self._get_repo_path(repo_id)
        if not repo_path.exists():
            return []

        def build_tree(path: Path) -> list[dict]:
            entries = []
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.name in EXCLUDE_DIRS:
                    continue
                if item.is_dir():
                    children = build_tree(item)
                    if children:
                        entries.append({
                            "name": item.name,
                            "path": str(item.relative_to(repo_path)),
                            "type": "dir",
                            "children": children,
                        })
                elif item.is_file():
                    if item.suffix.lower() not in INCLUDE_EXTENSIONS:
                        continue
                    if item.name in EXCLUDE_FILES:
                        continue
                    try:
                        if item.stat().st_size > MAX_FILE_SIZE:
                            continue
                    except OSError:
                        continue
                    entries.append({
                        "name": item.name,
                        "path": str(item.relative_to(repo_path)),
                        "type": "file",
                    })
            return entries

        return build_tree(repo_path)
