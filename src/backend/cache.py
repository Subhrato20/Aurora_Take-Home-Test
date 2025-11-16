"""Local cache implementation for November messages."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from .log_utils import logger


class LocalCache:
    """Stores retrieved messages locally so subsequent runs can re-use them."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._messages: List[Dict[str, Any]] = []
        self._ids: Set[str] = set()
        self._remote_total: Optional[int] = None
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            content = self._path.read_text(encoding="utf-8")
            if not content.strip():
                return
            raw = json.loads(content)
            self._messages = list(raw.get("messages") or [])
            self._remote_total = raw.get("remote_total")
            self._ids = {
                str(message.get("id") or "")
                for message in self._messages
                if message.get("id")
            }
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load local cache; starting empty")
            self._messages = []
            self._ids = set()
            self._remote_total = None

    def iter_pages(self, limit: int) -> Iterable[Dict[str, Any]]:
        total = len(self._messages)
        if total == 0:
            return
        for start in range(0, total, limit):
            yield {
                "total": self._remote_total or total,
                "items": self._messages[start : start + limit],
            }

    def append_items(
        self, items: Sequence[Dict[str, Any]], remote_total: Optional[int]
    ) -> None:
        if not items:
            return
        changed = False
        for item in items:
            item_id = str(item.get("id") or "")
            if item_id and item_id in self._ids:
                continue
            self._messages.append(item)
            if item_id:
                self._ids.add(item_id)
            changed = True
        if remote_total is not None:
            self._remote_total = remote_total
            changed = True
        if changed:
            self._persist()

    def _persist(self) -> None:
        payload = {
            "messages": self._messages,
            "remote_total": self._remote_total,
        }
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @property
    def cached_count(self) -> int:
        return len(self._messages)
