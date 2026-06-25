"""Recommender: rank eligible candidates and explain the top picks.

This is a good place for LLM judgment because "interesting" is subjective. But the
demo must work without a key, so we provide a deterministic fallback that ranks on
transparent signals (taste overlap with the reference purchases, condition, seller
trust, budget headroom, fewer risks). Both paths return identical `Recommendation`
shapes.

Important: the recommender only ever sees eligible candidates. It does not decide
hard eligibility (budget/broken/brand) - validation already did that.
"""

from __future__ import annotations

import json
import logging

from app.config import BUDGET_LIMIT_CENTS, llm_enabled
from app.llm.client import chat_json
from app.models import Candidate, Listing, Recommendation

logger = logging.getLogger(__name__)


def _sanitized(exc: Exception) -> str:
    """Concise, safe summary of an exception for logging.

    Only the exception class name and a truncated message - never tracebacks,
    payloads, headers, env vars, or secrets.
    """
    return f"{type(exc).__name__}: {str(exc)[:200]}"

# Tags that signal the vintage/collector character the collector is drawn to.
COLLECTOR_TAGS = {
    "vintage",
    "collector",
    "marlin",
    "deadstock",
    "new-old-stock",
    "promo-logo",
    "mechanical",
    "easy-reader",
}


def recommend(
    candidates: list[Candidate],
    profile: dict,
    references: list[Listing],
    top_n: int = 3,
) -> tuple[list[Recommendation], str]:
    """Return (recommendations, mode) where mode is "llm" or "fallback"."""
    if not candidates:
        return [], "fallback"

    if llm_enabled():
        try:
            return _recommend_llm(candidates, profile, references, top_n), "llm"
        except Exception as exc:
            # Any LLM/parse error degrades gracefully to the deterministic path.
            logger.warning("LLM recommender failed; using fallback: %s", _sanitized(exc))
    return _recommend_fallback(candidates, references, top_n), "fallback"


# --- Deterministic fallback -------------------------------------------------

def _reference_tags(references: list[Listing]) -> set[str]:
    """Union of style tags across the reference purchases (the taste fingerprint)."""
    tags: set[str] = set()
    for ref in references:
        tags.update(t.lower() for t in ref.style_tags)
    return tags


def _score(candidate: Candidate, ref_tags: set[str]) -> float:
    """Transparent taste score. Higher is better."""
    tags = {t.lower() for t in candidate.listing.style_tags}
    taste_overlap = len(tags & ref_tags)
    collector_bonus = len(tags & COLLECTOR_TAGS)
    seller = (candidate.listing.seller_rating or 0) / 100.0
    headroom = (BUDGET_LIMIT_CENTS - candidate.finance.total_cad_cents) / BUDGET_LIMIT_CENTS
    risk_penalty = len(candidate.risk_flags)

    # Weights kept simple and explainable for an interview walkthrough.
    return (
        2.0 * taste_overlap
        + 1.5 * collector_bonus
        + 1.0 * seller
        + 0.5 * headroom
        - 0.5 * risk_penalty
    )


def _fallback_reason(candidate: Candidate, ref_tags: set[str]) -> str:
    """Build a grounded, templated explanation from the listing's own fields."""
    tags = {t.lower() for t in candidate.listing.style_tags}
    matched = sorted(tags & (ref_tags | COLLECTOR_TAGS))
    parts = [f"Total landed cost ${candidate.finance.total_cad:.2f} CAD is within the $50 budget."]
    if matched:
        parts.append("Style overlaps with your taste: " + ", ".join(matched) + ".")
    if candidate.listing.working_status:
        parts.append(f"Working status: {candidate.listing.working_status}.")
    if candidate.listing.seller_rating:
        parts.append(f"Seller rating {candidate.listing.seller_rating}%.")
    return " ".join(parts)


def _recommend_fallback(
    candidates: list[Candidate], references: list[Listing], top_n: int
) -> list[Recommendation]:
    ref_tags = _reference_tags(references)
    # Sort by score desc, then cheaper total, then id for deterministic ties.
    ranked = sorted(
        candidates,
        key=lambda c: (-_score(c, ref_tags), c.finance.total_cad_cents, c.listing.id),
    )
    return [_to_recommendation(c, i + 1, _fallback_reason(c, ref_tags)) for i, c in enumerate(ranked[:top_n])]


# --- LLM path ---------------------------------------------------------------

def _recommend_llm(
    candidates: list[Candidate], profile: dict, references: list[Listing], top_n: int
) -> list[Recommendation]:
    by_id = {c.listing.id: c for c in candidates}

    system = (
        "You are a vintage Timex buying scout. You rank already-eligible listings by how "
        "well they fit one collector's taste and explain why. All listings shown are already "
        "within budget and not broken; do not re-check those constraints. Ground every reason "
        "in the listing's own fields. Return strict JSON."
    )
    user = json.dumps(
        {
            "instruction": (
                f"Pick exactly {top_n} listings (no more, no fewer) using only listing_id "
                "values from the candidates below, with no duplicates. For each return "
                "listing_id, why_it_matches (1-2 sentences grounded in the listing), and "
                'risk_notes (array of short strings). Respond as {"recommendations": [...]}.'
            ),
            "collector_profile": profile,
            "reference_purchases": [
                {
                    "title": r.title,
                    "style_tags": r.style_tags,
                    "taste_notes": r.taste_notes,
                    "why_user_liked_it": r.why_user_liked_it,
                }
                for r in references
            ],
            "candidates": [
                {
                    "listing_id": c.listing.id,
                    "title": c.listing.title,
                    "marketplace": c.listing.marketplace,
                    "total_cad": c.finance.total_cad,
                    "condition": c.listing.condition,
                    "working_status": c.listing.working_status,
                    "style_tags": c.listing.style_tags,
                    "description": c.listing.description,
                    "risk_flags": c.risk_flags,
                }
                for c in candidates
            ],
        }
    )

    data = chat_json(system, user)
    items = data.get("recommendations")

    # Enforce the product contract before accepting any LLM output. We expect one
    # pick per eligible listing up to top_n (so when >= top_n are eligible, exactly
    # top_n). If the LLM output violates this, we raise so the caller falls back to
    # the deterministic recommender. We never PARTIALLY accept LLM results - that
    # keeps behavior simple and easy to explain.
    expected = min(top_n, len(candidates))
    _validate_llm_items(items, by_id, expected)

    # Safe to build now: every id is known, unique, and the count is exact.
    return [
        _to_recommendation(
            by_id[item["listing_id"]],
            rank,
            item.get("why_it_matches", ""),
            item.get("risk_notes"),
        )
        for rank, item in enumerate(items, start=1)
    ]


def _validate_llm_items(items: object, by_id: dict[str, Candidate], expected: int) -> None:
    """Validate raw LLM recommendation items against the contract.

    Raises ValueError if the output is malformed, the count is wrong, or any id is
    unknown or duplicated. On success, `items` is guaranteed to be a list of dicts
    with exactly `expected` unique, known listing ids.
    """
    if not isinstance(items, list):
        raise ValueError("LLM recommendations field is missing or not a list")
    if len(items) != expected:
        raise ValueError(f"expected {expected} recommendations, got {len(items)}")

    ids = [item.get("listing_id") if isinstance(item, dict) else None for item in items]
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise ValueError("LLM returned unknown or missing listing id(s)")
    if len(set(ids)) != expected:
        raise ValueError("LLM returned duplicate listing id(s)")


# --- Shared helper ----------------------------------------------------------

def _to_recommendation(
    candidate: Candidate, rank: int, why: str, risk_notes: list[str] | None = None
) -> Recommendation:
    """Assemble a Recommendation, defaulting risk notes to the candidate's flags."""
    listing = candidate.listing
    return Recommendation(
        rank=rank,
        listing_id=listing.id,
        title=listing.title,
        marketplace=listing.marketplace,
        listing_url=listing.listing_url,
        image_url=listing.image_url,
        total_cad=candidate.finance.total_cad,
        why_it_matches=why,
        risk_notes=risk_notes if risk_notes is not None else list(candidate.risk_flags),
    )
