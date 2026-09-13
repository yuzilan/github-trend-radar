#!/usr/bin/env python3
"""Small transparent topic normalization helpers."""

from __future__ import annotations

import re


TOPIC_ALIASES = {
    "ai-agents": "ai-agent",
    "ai_agents": "ai-agent",
    "developer-tool": "developer-tools",
    "devtools": "developer-tools",
    "large-language-model": "llm",
    "large-language-models": "llm",
    "llms": "llm",
    "local_first": "local-first",
    "localfirst": "local-first",
}


def canonical_topic(value: str) -> str:
    """Return a conservative canonical label without inventing a taxonomy."""
    original = value.strip().lower()
    if not original:
        return ""
    normalized = re.sub(r"\s+", "-", original)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return TOPIC_ALIASES.get(original, TOPIC_ALIASES.get(normalized, normalized))


def normalize_topics(values: list[str] | None) -> tuple[list[str], dict[str, str]]:
    """Return unique canonical topics plus visible aliases that changed."""
    canonical: set[str] = set()
    aliases: dict[str, str] = {}
    for value in values or []:
        original = value.strip().lower()
        normalized = canonical_topic(value)
        if not normalized:
            continue
        canonical.add(normalized)
        if original != normalized:
            aliases[original] = normalized
    return sorted(canonical), dict(sorted(aliases.items()))
