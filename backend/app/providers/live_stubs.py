"""Placeholder live providers (eBay / Etsy).

These exist to document the provider seam: when API access is approved, each
class implements `fetch_raw` to call its marketplace API and return raw records
in roughly the same shape as the seed data. Normalization then maps them into the
shared schema. They intentionally raise for now so nothing silently depends on a
live integration during the MVP.
"""

from __future__ import annotations

from typing import Any

from app.providers.base import ListingProvider


class EbayProvider(ListingProvider):
    name = "ebay"

    def fetch_raw(self, query: str = "Timex") -> list[dict[str, Any]]:
        # TODO: call eBay Browse API (key approved) and return raw items.
        raise NotImplementedError("eBay live integration not implemented in MVP")


class EtsyProvider(ListingProvider):
    name = "etsy"

    def fetch_raw(self, query: str = "Timex") -> list[dict[str, Any]]:
        # TODO: call Etsy API (pending key approval) and return raw items.
        raise NotImplementedError("Etsy live integration not implemented in MVP")
