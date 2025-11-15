"""
FastAPI Q&A service that searches November API messages and validates answers with an OpenAI loop.
The validator loop pages through remote messages, filters candidates, and asks an LLM to confirm an answer.
Configure OPENAI_API_KEY, NOVEMBER_API_BASE, and related settings via environment variables or a .env file.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
import json
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Set

import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("november_qa_service")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


DEFAULT_HTTP_TIMEOUT = 12.0


class Settings(BaseSettings):
    """Application configuration loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    november_api_base: str = Field(
        default="https://november7-730026606190.europe-west1.run.app",
        alias="NOVEMBER_API_BASE",
    )
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    page_size: int = Field(default=100, alias="PAGE_SIZE", ge=1)
    max_validator_messages: int = Field(
        default=12, alias="MAX_VALIDATOR_MESSAGES", ge=1, le=20
    )
    name_resolver_max_names: int = Field(
        default=50, alias="NAME_RESOLVER_MAX_NAMES", ge=1, le=200
    )


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

    async def iterate_pages(self, limit: int) -> AsyncIterator[Dict[str, Any]]:
        """Yield message pages until the total count is exhausted."""
        skip = 0
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

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()


@dataclass
class ParsedQuestion:
    """Parsed structure that captures the member name and relevant keywords."""

    member_name: Optional[str] = None
    keywords: List[str] = field(default_factory=list)


@dataclass
class ValidatorResult:
    """Structured output from the LLM validator."""

    answer: str
    source_index: Optional[int] = None


@dataclass
class AnswerResult:
    """Result returned by the QA service."""

    answer: str
    message: Optional[Dict[str, Any]] = None


class QuestionParser:
    """Simple heuristic parser for extracting names and topic keywords."""

    _name_pattern = re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)")
    _token_pattern = re.compile(r"[A-Za-z0-9']+")
    _stop_words: Set[str] = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "with",
        "who",
        "what",
        "when",
        "where",
        "why",
        "how",
        "was",
        "were",
        "will",
        "has",
        "have",
        "her",
        "his",
        "him",
        "she",
        "he",
        "you",
        "your",
        "yours",
        "our",
        "ours",
        "my",
        "mine",
    }

    def parse(self, question: str) -> ParsedQuestion:
        """Return a lightweight parsed representation of the question."""
        member_name = self._extract_member_name(question)
        keywords = self._extract_keywords(question)
        # TODO: Swap this heuristic parser with an LLM-powered parser for richer extraction.
        return ParsedQuestion(member_name=member_name, keywords=keywords)

    def _extract_member_name(self, question: str) -> Optional[str]:
        matches = list(self._name_pattern.finditer(question))
        for match in reversed(matches):
            normalized = match.group().strip()
            if normalized and normalized.lower() not in self._stop_words:
                if not self._preceded_by_location_cue(question, match.start()):
                    return normalized
        return None

    def _preceded_by_location_cue(self, text: str, start: int) -> bool:
        """Check whether the capitalized phrase is likely a location (e.g., after 'to')."""
        prefix = text[:start].rstrip()
        if not prefix:
            return False
        tokens = self._token_pattern.findall(prefix)
        if not tokens:
            return False
        last_token = tokens[-1].lower()
        return last_token in {"to", "in", "at", "into", "onto", "towards", "from"}

    def _extract_keywords(self, question: str) -> List[str]:
        tokens = [token.lower() for token in self._token_pattern.findall(question)]
        keywords: List[str] = []
        seen: Set[str] = set()
        for token in tokens:
            if token in self._stop_words or len(token) <= 2:
                continue
            if token not in seen:
                keywords.append(token)
                seen.add(token)
        return keywords


class LLMValidator:
    """Wraps an OpenAI chat completion call that validates candidate answers."""

    def __init__(self, client: AsyncOpenAI, model: str, max_messages: int) -> None:
        self._client = client
        self._model = model
        self._max_messages = max_messages

    async def validate_and_answer(
        self,
        question: str,
        candidates: Sequence[Dict[str, Any]],
    ) -> ValidatorResult:
        """Return an answer if one of the candidates contains it, else NO_ANSWER."""
        if not candidates:
            return ValidatorResult(answer="NO_ANSWER")

        truncated = list(candidates[: self._max_messages])
        formatted_messages = []
        for idx, candidate in enumerate(truncated, start=1):
            user_name = str(candidate.get("user_name") or "unknown")
            message_text = str(candidate.get("message") or "")
            formatted_messages.append(f"{idx}. {user_name}: {message_text}")

        prompt = (
            "You must answer the user's question using only the candidate messages below.\n"
            "Rules:\n"
            "1. Use only the provided message text; ignore metadata.\n"
            "2. Quote facts only when the message explicitly states them.\n"
            "3. If a message answers the question, call the function with the answer text and the candidate number.\n"
            "4. If no message answers it, reply with NO_ANSWER.\n\n"
            f"Question: {question}\n\n"
            "Candidate messages:\n"
            + "\n".join(formatted_messages)
        )

        logger.info("Invoking LLM validator with %s candidate(s)", len(truncated))
        completion = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that must stick strictly to the provided messages."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "deliver_answer",
                        "description": (
                            "Use when one of the candidate messages answers the question."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "answer_text": {"type": "string"},
                                "source_number": {"type": "integer", "minimum": 1},
                            },
                            "required": ["answer_text", "source_number"],
                        },
                    },
                }
            ],
        )

        choice = completion.choices[0] if completion.choices else None
        if choice and choice.message and choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            try:
                payload = json.loads(tool_call.function.arguments)
                answer_text = str(payload.get("answer_text") or "").strip()
                source_number_raw = payload.get("source_number")
                source_number = (
                    int(source_number_raw) if source_number_raw is not None else None
                )
            except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
                logger.warning("Failed to parse validator tool response")
                return ValidatorResult(answer="NO_ANSWER")

            if answer_text:
                return ValidatorResult(answer=answer_text, source_index=source_number)

        message_content = ""
        if choice and choice.message and choice.message.content:
            message_content = choice.message.content.strip()

        if message_content.upper() == "NO_ANSWER":
            return ValidatorResult(answer="NO_ANSWER")

        return ValidatorResult(answer=message_content or "NO_ANSWER")


class LLMNameResolver:
    """Uses OpenAI function calling to select relevant member names from a page."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        max_names: int,
    ) -> None:
        self._client = client
        self._model = model
        self._max_names = max_names

    async def select_names(
        self,
        question: str,
        candidate_names: Sequence[str],
    ) -> Set[str]:
        """Return a set of user_name strings that match the input question."""
        filtered = [name.strip() for name in candidate_names if name and name.strip()]
        if not filtered:
            return set()

        # Preserve order and limit how many names are sent to the model.
        seen = set()
        ordered_unique = []
        for name in filtered:
            lower = name.lower()
            if lower not in seen:
                seen.add(lower)
                ordered_unique.append(name)
            if len(ordered_unique) >= self._max_names:
                break

        names_blob = "\n".join(
            f"{idx}. {name}" for idx, name in enumerate(ordered_unique, start=1)
        )
        user_prompt = (
            "Question:\n"
            f"{question}\n\n"
            "Available member names:\n"
            f"{names_blob}\n\n"
            "Return only the members whose names are clearly referenced or implied by the question."
        )

        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You pick member names from a provided list that match the question. "
                            "If none match, return an empty list."
                        ),
                    },
                    {"role": "user", "content": user_prompt},
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "select_member_names",
                            "description": (
                                "Return the member names from the list that best match the user's question."
                            ),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "selected_names": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    }
                                },
                                "required": ["selected_names"],
                            },
                        },
                    }
                ],
                tool_choice={
                    "type": "function",
                    "function": {"name": "select_member_names"},
                },
            )
        except Exception:
            logger.exception("Name resolver failed; falling back to heuristic name match")
            return set()

        choice = completion.choices[0] if completion.choices else None
        if not choice or not choice.message or not choice.message.tool_calls:
            return set()

        try:
            arguments = choice.message.tool_calls[0].function.arguments
            payload = json.loads(arguments)
            selected = payload.get("selected_names") or []
        except (json.JSONDecodeError, AttributeError, KeyError, IndexError, TypeError):
            logger.warning("Failed to parse name resolver response")
            return set()

        return {str(name).strip().lower() for name in selected if str(name).strip()}


class QAService:
    """Coordinates parsing, fetching, filtering, and LLM validation."""

    def __init__(
        self,
        fetcher: MessageFetcher,
        parser: QuestionParser,
        validator: LLMValidator,
        name_resolver: LLMNameResolver,
        page_size: int,
        fallback_answer: str = "I couldn't find the answer in the available messages.",
    ) -> None:
        self._fetcher = fetcher
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

        try:
            async for page in self._fetcher.iterate_pages(limit=self._page_size):
                items = page.get("items") or []
                logger.info("Evaluating page with %s message(s)", len(items))

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
                if validation.answer != "NO_ANSWER":
                    logger.info("Answer found via LLM validator")
                    source_message = self._select_source_message(
                        candidates, validation.source_index
                    )
                    return AnswerResult(answer=validation.answer, message=source_message)
        except RuntimeError as exc:
            logger.error(
                "Stopping search due to upstream API error; returning fallback", exc_info=exc
            )
            return AnswerResult(answer=self._fallback_answer)

        logger.info("All pages exhausted without finding an answer")
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


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    message: Optional[Dict[str, Any]] = None


settings = Settings()
message_fetcher = MessageFetcher(
    base_url=settings.november_api_base,
    timeout=DEFAULT_HTTP_TIMEOUT,
)
question_parser = QuestionParser()
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
    parser=question_parser,
    validator=llm_validator,
    name_resolver=name_resolver,
    page_size=settings.page_size,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown resources."""
    try:
        yield
    finally:
        await message_fetcher.aclose()


app = FastAPI(title="November Q&A Service", lifespan=lifespan)


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Answer the provided question via the QAService."""
    try:
        result = await qa_service.answer_question(request.question)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to answer question")
        raise HTTPException(
            status_code=500,
            detail="Unable to process the question right now.",
        ) from exc
    return AskResponse(answer=result.answer, message=result.message)


# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
