from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    openai_api_key: str = ""
    repos_dir: str = "./repos"
    chroma_dir: str = "./chroma_data"
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o"
    chunk_size: int = 1500
    chunk_overlap: int = 200
    max_context_chunks: int = 10

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
