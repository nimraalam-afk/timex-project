"""Deterministic validation: apply the collector's hard constraints.

Hard constraints are checked in code (not by the LLM) because correctness matters:
brand, is-a-watch, not explicitly broken, within budget, required fields present,
and a known marketplace. Every rejection records a human-readable reason so the
run is fully traceable. Non-blocking caution words (untested, dead battery, runs
slow) become risk flags for the recommender/evaluator to consider later.
"""

from __future__ import annotations

from app.config import KNOWN_MARKETPLACES, REQUIRED_BRAND
from app.models import Listing, ValidationResult
from app.pipeline.finance import safe_finance

# Condition/status text that means the watch is explicitly broken or sold for parts.
# The collector will replace a battery, but will not accept non-running / parts items.
BROKEN_CONDITION_KEYWORDS = (
    "for parts",
    "not working",
    "repair",
)
BROKEN_STATUS_KEYWORDS = (
    "not working",
    "broken",
    "not running",
    "parts only",
)

# Caution phrases that do NOT reject a listing but are surfaced as risk flags.
RISK_KEYWORDS = (
    "untested",
    "as-is",
    "as is",
    "needs battery",
    "dead battery",
    "battery needed",
    "runs slow",
    "running slow",
    "runs fast",
    "not serviced",
    "service",
    "unverified",
    "unknown",
)

# Fields that must be present for a listing to be considered at all.
REQUIRED_FIELDS = ("id", "title", "marketplace", "listing_url")


def _contains_any(text: str | None, keywords: tuple[str, ...]) -> bool:
    """Case-insensitive substring check against a list of keywords."""
    if not text:
        return False
    low = text.lower()
    return any(kw in low for kw in keywords)


def _collect_risk_flags(listing: Listing) -> list[str]:
    """Combine source risk_flags with caution keywords found in the listing text."""
    flags = list(listing.risk_flags)
    haystack = " ".join(
        part
        for part in (listing.working_status, listing.condition, listing.description, listing.title)
        if part
    )
    low = haystack.lower()
    for kw in RISK_KEYWORDS:
        if kw in low and kw not in flags:
            flags.append(kw)
    return flags


def validate_listing(listing: Listing) -> ValidationResult:
    """Run all hard constraints on a single listing and return a structured result."""
    reasons: list[str] = []

    # 1. Required fields present.
    for field in REQUIRED_FIELDS:
        if not getattr(listing, field, None):
            reasons.append(f"missing required field: {field}")

    # 2. Correct brand.
    if (listing.brand or "").strip().lower() != REQUIRED_BRAND.lower():
        reasons.append(f"brand is not {REQUIRED_BRAND}")

    # 3. Must actually be a watch (excludes parts lots, straps, jewelry, boxes).
    if not listing.is_watch:
        reasons.append("listing is not a watch")

    # 4. Known marketplace.
    if (listing.marketplace or "") not in KNOWN_MARKETPLACES:
        reasons.append("unknown marketplace")

    # 5. Not explicitly broken / for parts (battery replacement is acceptable).
    if _contains_any(listing.condition, BROKEN_CONDITION_KEYWORDS) or _contains_any(
        listing.working_status, BROKEN_STATUS_KEYWORDS
    ):
        reasons.append("explicitly broken or sold for parts")

    # 6. Budget: deterministic landed cost must be within the limit.
    finance = safe_finance(listing)
    if finance is None:
        reasons.append("missing price, shipping, or fx_rate_to_cad")
    elif not finance.within_budget:
        reasons.append("over budget after shipping and FX")

    return ValidationResult(
        listing_id=listing.id,
        is_eligible=len(reasons) == 0,
        rejection_reasons=reasons,
        risk_flags=_collect_risk_flags(listing),
        finance=finance,
    )


def validate_listings(listings: list[Listing]) -> list[ValidationResult]:
    """Validate many listings, preserving order for a stable audit trail."""
    return [validate_listing(listing) for listing in listings]
