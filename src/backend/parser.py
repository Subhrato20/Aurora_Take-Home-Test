"""Question parsing utilities."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class ParsedQuestion:
    """Parsed structure that captures the member name and relevant keywords."""

    member_name: Optional[str] = None
    keywords: List[str] = field(default_factory=list)


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
