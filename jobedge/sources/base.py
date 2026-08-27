"""Uniform interface every external job source implements.

The Fetcher layer never contains source-specific parsing — all of that
lives behind Source.fetch(). Adding a source means writing one new file
and decorating its class with @register; nothing else changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type

from jobedge.config import Config

# Every Source.fetch() row must have exactly these keys. Missing values are
# None, never "" or "N/A".
NORMALIZED_KEYS = (
    "source",
    "external_id",
    "title",
    "company",
    "location",
    "url",
    "description",
    "posted_at",
    "raw",
)


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self, config: Config) -> list[dict]:
        """Return normalized rows (see NORMALIZED_KEYS)."""
        raise NotImplementedError


SOURCES: dict[str, Type[Source]] = {}


def register(cls: Type[Source]) -> Type[Source]:
    """Class decorator: adds cls to the SOURCES registry under cls.name."""
    SOURCES[cls.name] = cls
    return cls


def normalize_row(
    source: str,
    external_id: str | None,
    title: str | None,
    company: str | None,
    location: str | None,
    url: str | None,
    description: str | None,
    posted_at: str | None,
    raw: str | None = None,
) -> dict:
    return {
        "source": source,
        "external_id": external_id,
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": description,
        "posted_at": posted_at,
        "raw": raw,
    }
