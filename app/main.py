from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .messages_client import load_messages
from .qa import MessageIndex

logger = logging.getLogger(__name__)

app = FastAPI(title="Aurora QA", version="0.1.0")

index: Optional[MessageIndex] = None


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@app.on_event("startup")
async def startup_event() -> None:
    global index
    try:
        messages = load_messages()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Failed to load member messages: %s", exc)
        raise
    index = MessageIndex(messages)
    logger.info("Loaded %s messages into the index", len(messages))


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(payload: AskRequest) -> AskResponse:
    if index is None:
        raise HTTPException(status_code=503, detail="Knowledge base is still loading.")
    result = index.answer(payload.question)
    return AskResponse(answer=result.answer)
