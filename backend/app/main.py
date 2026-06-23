from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings

logger = structlog.get_logger()

app = FastAPI(title="DeepWiki", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "DeepWiki API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
