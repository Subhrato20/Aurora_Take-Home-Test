from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence

import requests
from pydantic import BaseModel

from .config import settings


class MessageRecord(BaseModel):
    id: str
    user_id: str
    user_name: str
    timestamp: datetime
    message: str


@dataclass
class MessageAPIClient:
    """Thin wrapper for the public /messages endpoint."""

    base_url: str = str(settings.message_api_base_url).rstrip("/")

    def __post_init__(self) -> None:
        self.base_url = str(self.base_url).rstrip("/")
        self._session = requests.Session()

    def fetch_messages(self, page_size: int | None = None) -> List[MessageRecord]:
        size = page_size or settings.message_page_size
        collected: List[MessageRecord] = []
        skip = 0
        total = None
        while True:
            payload = self._request_page(skip=skip, limit=size)
            items = payload.get("items", [])
            total = payload.get("total", len(items))
            collected.extend(MessageRecord(**item) for item in items)
            skip += size
            if len(collected) >= total:
                break
        return collected

    def _request_page(self, *, skip: int, limit: int) -> dict:
        resp = self._session.get(
            f"{self.base_url}/messages/",
            params={"skip": skip, "limit": limit},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


def load_messages() -> Sequence[MessageRecord]:
    client = MessageAPIClient()
    return client.fetch_messages()
