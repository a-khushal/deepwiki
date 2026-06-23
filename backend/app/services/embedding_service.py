import time
from abc import ABC, abstractmethod

from openai import OpenAI
import structlog

from app.config import settings

logger = structlog.get_logger()


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        ...


class OpenAIEmbedding(EmbeddingProvider):
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.batch_size = 100
        self.max_retries = 3

    def embed(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            embeddings = self._embed_batch(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        result = self._embed_batch([text])
        return result[0]

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                embeddings = [item.embedding for item in response.data]
                return embeddings
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning("embed_retry", attempt=attempt, error=str(e), wait=wait)
                    time.sleep(wait)
                else:
                    logger.error("embed_failed", error=str(e))
                    raise
        return []


class EmbeddingService:
    def __init__(self):
        self._provider: EmbeddingProvider = OpenAIEmbedding()

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    def set_provider(self, provider: EmbeddingProvider):
        self._provider = provider

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._provider.embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._provider.embed_query(text)
