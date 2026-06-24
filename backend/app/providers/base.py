"""Provider abstraction.

A provider's only job is deterministic retrieval: return raw listing records for
a brand/keyword. Normalization and validation happen later in the pipeline, so a
new marketplace integration only needs to implement `fetch_raw`. This is the seam
that lets us swap seed data for live eBay/Etsy data without touching the rest of
the system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ListingProvider(ABC):
    """Interface every marketplace provider implements."""

    #: Human-readable provider name, used in logs/traces.
    name: str = "base"

    @abstractmethod
    def fetch_raw(self, query: str = "Timex") -> list[dict[str, Any]]:
        """Return a bounded pool of raw listing dicts for the given query.

        Providers should apply only broad provider-side constraints (keyword,
        category, rough price). They must NOT encode the full collector taste
        model or hard budget/condition rules; that is the pipeline's job.
        """
        raise NotImplementedError
