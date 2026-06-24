"""Light orchestrator: coordinates the pipeline, holds no domain intelligence.

It runs the steps in order - load profile/references, fetch, normalize, validate,
recommend, evaluate - and returns one traceable `ScoutResult` describing what
happened at each stage. The meaningful judgment lives in the recommender and
evaluator; this module just wires steps together and records the trace.
"""

from __future__ import annotations

import json

from app.config import COLLECTOR_PROFILE_PATH, REFERENCE_PURCHASES_PATH
from app.models import Candidate, Exclusion, ScoutResult
from app.pipeline.evaluate import evaluate
from app.pipeline.normalize import normalize_listings
from app.pipeline.recommend import recommend
from app.pipeline.validate import validate_listings
from app.providers.base import ListingProvider
from app.providers.seed_provider import SeedProvider


def _load_profile() -> dict:
    """Load the stored collector profile (taste, budget, condition rules)."""
    with open(COLLECTOR_PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_references() -> list:
    """Load the three reference purchases as normalized Listings (taste examples)."""
    with open(REFERENCE_PURCHASES_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return normalize_listings(raw)


def run_scout(provider: ListingProvider | None = None, top_n: int = 3) -> ScoutResult:
    """Run the full pipeline and return a single traceable result object."""
    provider = provider or SeedProvider()
    profile = _load_profile()
    references = _load_references()

    # 1-3. Deterministic: fetch -> normalize -> validate.
    raw = provider.fetch_raw()
    listings = normalize_listings(raw)
    validations = validate_listings(listings)

    listings_by_id = {l.id: l for l in listings}

    # Build eligible candidates (listing + finance + risk flags) and the exclusion trail.
    candidates: list[Candidate] = []
    exclusions: list[Exclusion] = []
    for v in validations:
        if v.is_eligible and v.finance is not None:
            candidates.append(
                Candidate(
                    listing=listings_by_id[v.listing_id],
                    finance=v.finance,
                    risk_flags=v.risk_flags,
                )
            )
        else:
            exclusions.append(Exclusion(listing_id=v.listing_id, reasons=v.rejection_reasons))

    # 4-5. Judgment: recommend top N, then evaluate them. Both have fallbacks.
    recommendations, recommender_mode = recommend(candidates, profile, references, top_n)
    evaluator_notes, evaluator_mode = evaluate(recommendations, candidates, profile)

    counts = {
        "raw": len(raw),
        "normalized": len(listings),
        "eligible": len(candidates),
        "excluded": len(exclusions),
        "recommended": len(recommendations),
    }

    return ScoutResult(
        profile_summary=profile.get("summary", ""),
        counts=counts,
        exclusions=exclusions,
        recommendations=recommendations,
        evaluator_notes=evaluator_notes,
        recommender_mode=recommender_mode,
        evaluator_mode=evaluator_mode,
        llm_used=(recommender_mode == "llm" or evaluator_mode == "llm"),
    )
