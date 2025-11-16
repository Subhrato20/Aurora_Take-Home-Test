"""Core QA service orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .cache import LocalCache
from .fetcher import MessageFetcher
from .log_utils import logger
from .parser import ParsedQuestion, QuestionParser
from .validators import LLMNameResolver, LLMValidator, ValidatorResult


@dataclass
class AnswerResult:
    """Result returned by the QA service."""

    answer: str
    message: Optional[Dict[str, Any]] = None


class QAService:
    """Coordinates parsing, fetching, filtering, and LLM validation."""

    def __init__(
        self,
        fetcher: MessageFetcher,
        cache: LocalCache,
        parser: QuestionParser,
        validator: LLMValidator,
        name_resolver: LLMNameResolver,
        page_size: int,
        fallback_answer: str = "I couldn't find the answer in the available messages.",
    ) -> None:
        self._fetcher = fetcher
        self._cache = cache
        self._parser = parser
        self._validator = validator
        self._name_resolver = name_resolver
        self._page_size = page_size
        self._fallback_answer = fallback_answer

    async def answer_question(self, question: str) -> AnswerResult:
        """Return the best answer for the question, or a fallback message."""
        cleaned_question = question.strip()
        if not cleaned_question:
            return AnswerResult(answer="Please provide a non-empty question.")

        parsed = self._parser.parse(cleaned_question)
        logger.info(
            "Parsed question -> member_name=%s keywords=%s",
            parsed.member_name,
            parsed.keywords,
        )

        best_result: Optional[AnswerResult] = None
        best_score: Tuple[int, datetime] = (
            -1,
            datetime.min.replace(tzinfo=timezone.utc),
        )

        async def process_page(page: Dict[str, Any], source: str) -> None:
            nonlocal best_result, best_score
            items = page.get("items") or []
            logger.info(
                "Evaluating %s page with %s message(s)", source, len(items)
            )
            if not items:
                return

            page_names = [
                str(item.get("user_name") or "")
                for item in items
                if item.get("user_name")
            ]
            resolved_names = await self._name_resolver.select_names(
                cleaned_question, page_names
            )

            candidates = self._filter_candidates(items, parsed, resolved_names)
            logger.info("Found %s candidate message(s)", len(candidates))

            validation = await self._validator.validate_and_answer(
                cleaned_question,
                candidates,
            )
            if validation.answer == "NO_ANSWER":
                return

            logger.info("Candidate answer found via LLM validator")
            source_message = self._select_source_message(
                candidates, validation.source_index
            )
            score = self._score_candidate(source_message, parsed)
            if score > best_score:
                best_score = score
                best_result = AnswerResult(
                    answer=validation.answer,
                    message=source_message,
                )

        for page in self._cache.iter_pages(self._page_size):
            await process_page(page, "cached")

        remote_start = self._cache.cached_count

        try:
            async for page in self._fetcher.iterate_pages(
                limit=self._page_size, start=remote_start
            ):
                await process_page(page, "remote")
                self._cache.append_items(page.get("items") or [], page.get("total"))
        except RuntimeError as exc:
            logger.error(
                "Stopping search due to upstream API error; evaluating available answers",
                exc_info=exc,
            )
            if best_result:
                logger.info("Returning best answer found before API error")
                return best_result
            return AnswerResult(answer=self._fallback_answer)

        logger.info("All pages exhausted without finding an answer")
        if best_result:
            logger.info("Returning best accumulated answer after full search")
            return best_result
        return AnswerResult(answer=self._fallback_answer)

    def _filter_candidates(
        self,
        items: Sequence[Dict[str, Any]],
        parsed: ParsedQuestion,
        resolved_names: Set[str],
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        resolved_targets = {name.lower() for name in resolved_names if name}
        for item in items:
            user_name = str(item.get("user_name") or "")
            message_text = str(item.get("message") or "")

            if resolved_targets:
                if user_name.lower() not in resolved_targets:
                    continue
            elif parsed.member_name:
                if parsed.member_name.lower() not in user_name.lower():
                    continue

            if parsed.keywords:
                lowered = message_text.lower()
                if not any(keyword in lowered for keyword in parsed.keywords):
                    continue

            candidates.append(item)
        return candidates

    def _select_source_message(
        self,
        candidates: Sequence[Dict[str, Any]],
        source_index: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        if source_index:
            idx = source_index - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _score_candidate(
        self,
        message: Optional[Dict[str, Any]],
        parsed: ParsedQuestion,
    ) -> Tuple[int, datetime]:
        """Score a candidate by keyword coverage and recency."""
        if not message:
            return (0, datetime.min.replace(tzinfo=timezone.utc))

        message_text = str(message.get("message") or "").lower()
        keyword_matches = 0
        if parsed.keywords:
            keyword_matches = sum(1 for kw in parsed.keywords if kw in message_text)

        timestamp_raw = message.get("timestamp")
        timestamp_dt = datetime.min.replace(tzinfo=timezone.utc)
        if timestamp_raw:
            try:
                parsed_ts = datetime.fromisoformat(str(timestamp_raw))
                if parsed_ts.tzinfo is None:
                    parsed_ts = parsed_ts.replace(tzinfo=timezone.utc)
                timestamp_dt = parsed_ts
            except ValueError:
                logger.debug("Unable to parse timestamp '%s'", timestamp_raw)

        return (keyword_matches, timestamp_dt)
