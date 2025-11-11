from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from .config import settings
from .messages_client import MessageRecord


@dataclass
class AnswerResult:
    answer: str
    score: float
    message: MessageRecord | None


class MessageIndex:
    """Lightweight lexical index over the concierge messages."""

    def __init__(self, messages: Sequence[MessageRecord]):
        self.messages = list(messages)
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._user_to_indices: Dict[str, List[int]] = {}
        self._name_tokens: Dict[str, List[str]] = {}
        if self.messages:
            self._build_index()

    def _build_index(self) -> None:
        corpus = [record.message for record in self.messages]
        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._matrix = self._vectorizer.fit_transform(corpus)
        for idx, record in enumerate(self.messages):
            self._user_to_indices.setdefault(record.user_name, []).append(idx)
            self._name_tokens[record.user_name] = _tokenize_name(record.user_name)

    def answer(self, question: str) -> AnswerResult:
        if not question.strip():
            return AnswerResult(
                answer="Please supply a question so I can help.",
                score=0.0,
                message=None,
            )
        if not self.messages or self._vectorizer is None or self._matrix is None:
            return AnswerResult(
                answer="The member knowledge base has not finished loading yet.",
                score=0.0,
                message=None,
            )

        doc = self._vectorizer.transform([question])
        rowspace = self._matrix
        mapping = list(range(len(self.messages)))
        user_filtered = self._filter_indices_by_user(question)
        if user_filtered:
            rowspace = self._matrix[user_filtered]
            mapping = user_filtered

        if rowspace.shape[0] == 0:
            return AnswerResult(
                answer="I could not find that information in the member messages.",
                score=0.0,
                message=None,
            )

        scores = linear_kernel(doc, rowspace).flatten()
        best_position = int(np.argmax(scores))
        best_score = float(scores[best_position])
        message = self.messages[mapping[best_position]]

        if best_score < settings.min_similarity:
            return AnswerResult(
                answer="I could not find that information in the member messages.",
                score=best_score,
                message=None,
            )

        formatted = (
            f"{message.user_name} mentioned on {message.timestamp:%Y-%m-%d}: "
            f"{message.message}"
        )
        return AnswerResult(answer=formatted, score=best_score, message=message)

    def _filter_indices_by_user(self, question: str) -> List[int]:
        lowered = question.lower()
        matches: List[int] = []
        for user, tokens in self._name_tokens.items():
            if any(token in lowered for token in tokens):
                matches.extend(self._user_to_indices.get(user, []))
        return sorted(set(matches))


def _tokenize_name(name: str) -> List[str]:
    normalized = re.sub(r"[^a-zA-Z\s]", " ", name).lower()
    return [piece for piece in normalized.split() if piece]
