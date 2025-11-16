"""
FastAPI Q&A service that searches November API messages and validates answers with an OpenAI loop.
The validator loop pages through remote messages, filters candidates, and asks an LLM to confirm an answer.
Configure OPENAI_API_KEY, NOVEMBER_API_BASE, and related settings via environment variables or a .env file.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from .cache import LocalCache
from .config import DEFAULT_HTTP_TIMEOUT, Settings
from .fetcher import MessageFetcher
from .log_utils import logger
from .parser import QuestionParser
from .qa_service import AnswerResult, QAService
from .schemas import AskRequest, AskResponse
from .validators import LLMNameResolver, LLMValidator

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown resources."""
    try:
        yield
    finally:
        await message_fetcher.aclose()


app = FastAPI(title="November Q&A Service", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Answer the provided question via the QAService."""
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


# Run with: PYTHONPATH=src uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
