"""
FastAPI Q&A service that searches November API messages and validates answers with an OpenAI loop.
The validator loop pages through remote messages, filters candidates, and asks an LLM to confirm an answer.
Configure OPENAI_API_KEY, NOVEMBER_API_BASE, and related settings via environment variables or a .env file.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from openai import AsyncOpenAI

from .cache import LocalCache
from .config import DEFAULT_HTTP_TIMEOUT, Settings
from .fetcher import MessageFetcher
from .log_utils import logger
from .parser import QuestionParser
from .qa_service import AnswerResult, QAService
from .schemas import AskRequest, AskResponse
from .validators import LLMNameResolver, LLMValidator

try:
    settings = Settings()
    message_fetcher = MessageFetcher(
        base_url=settings.november_api_base,
        timeout=DEFAULT_HTTP_TIMEOUT,
    )
    question_parser = QuestionParser()
    local_cache = LocalCache(settings.cache_path)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    llm_validator = LLMValidator(
        client=openai_client,
        model=settings.openai_model,
        max_messages=settings.max_validator_messages,
    )
    name_resolver = LLMNameResolver(
        client=openai_client,
        model=settings.openai_model,
        max_names=settings.name_resolver_max_names,
    )
    qa_service = QAService(
        fetcher=message_fetcher,
        cache=local_cache,
        parser=question_parser,
        validator=llm_validator,
        name_resolver=name_resolver,
        page_size=settings.page_size,
    )
    logger.info("✅ All services initialized successfully")
except Exception as e:
    logger.exception("❌ Failed to initialize services: %s", e)
    # Set to None so we can check later
    qa_service = None
    settings = None
    message_fetcher = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown resources."""
    try:
        yield
    finally:
        if message_fetcher is not None:
            await message_fetcher.aclose()


app = FastAPI(title="November Q&A Service", lifespan=lifespan)

# Log startup info
logger.info(f"🚀 Starting server on port {os.getenv('PORT', '8000')}")
logger.info(f"Python path: {os.getenv('PYTHONPATH', 'not set')}")

# Add CORS middleware - allow all origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since frontend is served from same domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes must be defined BEFORE the catch-all frontend route
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Answer the provided question via the QAService."""
    if qa_service is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized. Check server logs and ensure OPENAI_API_KEY is set.",
        )
    try:
        result: AnswerResult = await qa_service.answer_question(request.question)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to answer question")
        raise HTTPException(
            status_code=500,
            detail="Unable to process the question right now.",
        ) from exc
    return AskResponse(answer=result.answer, message=result.message)


# Serve static files from frontend dist directory (must be after API routes)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
logger.info(f"Looking for frontend at: {frontend_dist}")
logger.info(f"Frontend exists: {frontend_dist.exists()}")
if frontend_dist.exists():
    logger.info(f"✅ Frontend found! Serving from {frontend_dist}")
    # Mount static assets (JS, CSS, etc.)
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Serve vite.svg if it exists
    vite_svg = frontend_dist / "vite.svg"
    if vite_svg.exists():
        @app.get("/vite.svg")
        async def serve_vite_svg():
            return FileResponse(vite_svg)
    
    # Serve index.html for all non-API routes (SPA routing) - MUST BE LAST
    # Note: FastAPI matches more specific routes first, so /docs, /openapi.json, /ask (POST) will work
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Exclude API and documentation paths (these are handled by FastAPI automatically)
        if full_path in ("docs", "openapi.json", "redoc") or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        # Serve index.html for all other routes (SPA handles client-side routing)
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend not built")
else:
    # Frontend not built yet, show API info at root
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "service": "November Q&A Service",
            "status": "running",
            "docs": "/docs",
            "endpoints": {
                "ask": "/ask (POST)",
                "docs": "/docs",
                "health": "/health",
            },
            "note": "Frontend not built. Run 'npm run build' in src/frontend",
        }


# Run with: PYTHONPATH=src uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
