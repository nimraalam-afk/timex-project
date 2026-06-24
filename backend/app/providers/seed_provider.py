"""Seed data provider: the reliable default source.

Seed listings are a deliberate part of the design, not a shortcut. API approvals
can be slow and scraping is brittle, so seeded (but realistically shaped) data
lets the full product experience run reliably. The seeded records already match
the normalized schema, so this provider just loads them from disk.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import SEED_LISTINGS_PATH
from app.providers.base import ListingProvider


class SeedProvider(ListingProvider):
    """Loads candidate listings from the bundled seed JSON file."""

    name = "seed"

    def __init__(self, path=SEED_LISTINGS_PATH) -> None:
        self._path = path

    def fetch_raw(self, query: str = "Timex") -> list[dict[str, Any]]:
        """Read every seed listing. The query is accepted for interface parity
        but not used for filtering here, since the seed pool is already bounded.
        """
        with open(self._path, "r", encoding="utf-8") as f:
            records: list[dict[str, Any]] = json.load(f)
        return records
