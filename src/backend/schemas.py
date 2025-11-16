"""Pydantic request/response models."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    message: Optional[Dict[str, Any]] = None
