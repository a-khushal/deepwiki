from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.api.routes.repo import router as repo_router
from app.api.routes.chat import router as chat_router
from app.api.routes.docs import router as docs_router
from app.services.mcp_service import router as mcp_router
from app.config import settings

logger = structlog.get_logger()

app = FastAPI(title="DeepWiki", version="0.1.0")

app.include_router(repo_router)
app.include_router(chat_router)
app.include_router(docs_router)
app.include_router(mcp_router)

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
