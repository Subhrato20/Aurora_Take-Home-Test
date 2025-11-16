"""HTTP client for November messages API."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .log_utils import logger


class MessageFetcher:
    """Fetches paginated messages from the November API."""

    def __init__(self, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def fetch_page(self, skip: int, limit: int) -> Dict[str, Any]:
        """Fetch a single page of messages and validate the response."""
        logger.info("Fetching messages: skip=%s limit=%s", skip, limit)
        try:
            response = await self._client.get(
                "/messages/",
                params={"skip": skip, "limit": limit},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "November API returned non-200 status: %s",
                exc.response.status_code,
                exc_info=exc,
            )
            raise RuntimeError("November API responded with an error") from exc
        except httpx.RequestError as exc:
            logger.error("Failed to reach November API", exc_info=exc)
            raise RuntimeError("Unable to reach November API") from exc

        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected response format from November API")
        return data

    async def iterate_pages(
        self, limit: int, start: int = 0
    ) -> AsyncIterator[Dict[str, Any]]:
        """Yield message pages until the total count is exhausted."""
        skip = start
        total: Optional[int] = None

        while total is None or skip < total:
            page = await self.fetch_page(skip=skip, limit=limit)
            yield page

            items = page.get("items") or []
            total_value = page.get("total")
            if isinstance(total_value, int):
                total = total_value
            else:
                try:
                    total = int(total_value)
                except (TypeError, ValueError):
                    pass
            skip += limit

            if not items:
                break
            await asyncio.sleep(5)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
