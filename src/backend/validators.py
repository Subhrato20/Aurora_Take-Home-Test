"""LLM powered validators and name resolvers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence, Set

from openai import AsyncOpenAI

from .log_utils import logger


@dataclass
class ValidatorResult:
    """Structured output from the LLM validator."""

    answer: str
    source_index: int | None = None


class LLMValidator:
    """Wraps an OpenAI chat completion call that validates candidate answers."""

    def __init__(self, client: AsyncOpenAI, model: str, max_messages: int) -> None:
        self._client = client
        self._model = model
        self._max_messages = max_messages

    async def validate_and_answer(
        self,
        question: str,
        candidates: Sequence[dict[str, Any]],
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
            temperature=0.1,
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
                temperature=0.1,
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
        except (
            json.JSONDecodeError,
            AttributeError,
            KeyError,
            IndexError,
            TypeError,
        ):
            logger.warning("Failed to parse name resolver response")
            return set()

        return {str(name).strip().lower() for name in selected if str(name).strip()}
