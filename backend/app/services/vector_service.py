import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError
import structlog

from app.config import settings
from app.models.schemas import CodeChunk, SearchResult

logger = structlog.get_logger()


class VectorService:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _collection_name(self, repo_id: str) -> str:
        return repo_id.replace("-", "_").replace(".", "_")

    def store_chunks(self, repo_id: str, chunks: list[CodeChunk], embeddings: list[list[float]]):
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must match")

        collection = self._get_or_create_collection(repo_id)

        ids = [str(uuid.uuid4()) for _ in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "file_path": chunk.file_path,
                "language": chunk.language,
                "symbol_name": chunk.symbol_name or "",
                "symbol_type": chunk.symbol_type or "",
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ]

        batch_size = 500
        for i in range(0, len(chunks), batch_size):
            end = min(i + batch_size, len(chunks))
            collection.add(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )

        logger.info("stored_chunks", repo_id=repo_id, count=len(chunks))

    def query(self, repo_id: str, query_embedding: list[float], top_k: int = 10) -> list[SearchResult]:
        collection = self._get_collection(repo_id)
        if not collection:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, 50),
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        search_results = []
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            score = results["distances"][0][i] if results["distances"] else 0.0

            chunk = CodeChunk(
                repo_id=repo_id,
                file_path=metadata.get("file_path", ""),
                language=metadata.get("language", ""),
                symbol_name=metadata.get("symbol_name") or None,
                symbol_type=metadata.get("symbol_type") or None,
                start_line=int(metadata.get("start_line", 0)),
                end_line=int(metadata.get("end_line", 0)),
                chunk_index=int(metadata.get("chunk_index", 0)),
                content=results["documents"][0][i] if results["documents"] else "",
            )
            search_results.append(SearchResult(chunk=chunk, score=score))

        return search_results

    def delete_collection(self, repo_id: str):
        name = self._collection_name(repo_id)
        try:
            self.client.delete_collection(name)
            logger.info("deleted_collection", repo_id=repo_id)
        except ValueError:
            pass

    def collection_exists(self, repo_id: str) -> bool:
        name = self._collection_name(repo_id)
        try:
            self.client.get_collection(name)
            return True
        except (ValueError, NotFoundError):
            return False

    def _get_or_create_collection(self, repo_id: str):
        name = self._collection_name(repo_id)
        return self.client.get_or_create_collection(
            name=name,
            metadata={"repo_id": repo_id},
        )

    def _get_collection(self, repo_id: str):
        name = self._collection_name(repo_id)
        try:
            return self.client.get_collection(name)
        except ValueError:
            return None
