"""Normalization: raw provider records -> validated `Listing` models.

The seed data is already shaped to the normalized schema, so this step is mostly
parsing/coercion today. It still lives behind one function because a live provider
would map its API fields here, giving the rest of the pipeline a single, consistent
shape to work with regardless of source.
"""

from __future__ import annotations

from typing import Any

from app.models import Listing


def normalize_listings(raw_records: list[dict[str, Any]]) -> list[Listing]:
    """Convert raw dicts into `Listing` models.

    Records that cannot be parsed at all are skipped rather than crashing the run,
    keeping the pipeline robust to occasional bad data. (Hard business rules are
    applied later in validation, not here.)
    """
    listings: list[Listing] = []
    for record in raw_records:
        try:
            listings.append(Listing.model_validate(record))
        except Exception:
            # Skip unparseable records; deterministic validation handles the rest.
            continue
    return listings
