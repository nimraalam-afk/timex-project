"""Pydantic models for the shared normalized schema and deterministic outputs.

The `Listing` model mirrors data/normalized_listing_schema.json so candidate
listings and reference purchases share one shape across the whole pipeline.
Fields are optional/defaulted because real marketplace data is often incomplete;
deterministic validation (not the schema) decides whether a listing is usable.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Listing(BaseModel):
    """One normalized record: either a candidate listing or a reference purchase."""

    # Identity / source
    id: str
    record_type: str  # "candidate_listing" or "reference_purchase"
    brand: Optional[str] = None
    model: Optional[str] = None
    title: Optional[str] = None
    marketplace: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    listing_url: Optional[str] = None
    image_url: Optional[str] = None
    availability_state: Optional[str] = None
    is_watch: bool = False

    # Money (raw, as provided by the source). The pipeline recomputes CAD totals.
    price: Optional[float] = None
    shipping: Optional[float] = None
    currency: Optional[str] = None
    fx_rate_to_cad: Optional[float] = None
    total_price_cad: Optional[float] = None  # precomputed by source; treated as a hint only
    within_budget: Optional[bool] = None  # precomputed by source; treated as a hint only
    budget_limit_cad: Optional[float] = None
    budget_basis: Optional[str] = None
    ships_to_postal_code: Optional[str] = None

    # Condition / description
    condition: Optional[str] = None
    working_status: Optional[str] = None
    description: Optional[str] = None
    watch_type: Optional[str] = None
    movement: Optional[str] = None
    style_tags: list[str] = Field(default_factory=list)
    visual_style_notes: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)

    # Seller signals
    seller_name: Optional[str] = None
    seller_rating: Optional[float] = None
    seller_feedback_count: Optional[int] = None
    seller_positive_feedback_percent: Optional[float] = None
    seller_location: Optional[str] = None
    seller_type: Optional[str] = None

    # Taste / annotation fields (used mostly by reference purchases and later steps)
    candidate_quality: Optional[str] = None
    match_notes: Optional[str] = None
    preference_signals: list[str] = Field(default_factory=list)
    taste_notes: Optional[str] = None
    why_user_liked_it: Optional[str] = None
    purchase_context: Optional[str] = None
    reference_notes: Optional[str] = None
    item_details: dict[str, Any] = Field(default_factory=dict)


class FinanceBreakdown(BaseModel):
    """Transparent, deterministic landed-cost calculation in integer cents.

    Kept separate from the Listing so the UI can show exactly how eligibility was
    computed (item + shipping, converted to CAD) and so money math is never the
    LLM's responsibility.
    """

    item_cents: int
    shipping_cents: int
    fx_rate_to_cad: float
    total_cad_cents: int
    within_budget: bool

    @property
    def total_cad(self) -> float:
        """Convenience dollar value for display (derived from integer cents)."""
        return round(self.total_cad_cents / 100, 2)


class ValidationResult(BaseModel):
    """Outcome of deterministic hard-constraint validation for one listing."""

    listing_id: str
    is_eligible: bool
    # Reasons a listing was rejected (empty when eligible). Drives the audit trail.
    rejection_reasons: list[str] = Field(default_factory=list)
    # Non-blocking caution signals (e.g. untested, dead battery) for downstream steps.
    risk_flags: list[str] = Field(default_factory=list)
    finance: Optional[FinanceBreakdown] = None


class Candidate(BaseModel):
    """An eligible listing bundled with its computed finance and risk flags.

    This is the only thing the recommender/evaluator see: validation has already
    guaranteed eligibility, so these steps focus purely on judgment, never on hard
    constraints.
    """

    listing: Listing
    finance: FinanceBreakdown
    risk_flags: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    """A single ranked purchase candidate with its reasoning.

    Same shape whether produced by the LLM or the deterministic fallback, so the
    rest of the system never needs to know which path generated it.
    """

    rank: int
    listing_id: str
    title: Optional[str] = None
    marketplace: Optional[str] = None
    listing_url: Optional[str] = None
    image_url: Optional[str] = None
    total_cad: float
    why_it_matches: str
    risk_notes: list[str] = Field(default_factory=list)


class EvaluatorNote(BaseModel):
    """Lightweight quality-gate verdict for one recommendation."""

    listing_id: str
    verdict: str  # "ok" or "warn"
    note: str


class Exclusion(BaseModel):
    """A rejected listing and why, for the run's audit trail."""

    listing_id: str
    reasons: list[str]


class ScoutResult(BaseModel):
    """The single traceable object the orchestrator returns.

    Captures what happened at each stage so the run can be inspected end to end:
    stage counts, exclusions with reasons, the recommendations, the evaluator's
    notes, and whether real LLM calls or deterministic fallbacks were used.
    """

    profile_summary: str
    counts: dict[str, int]
    exclusions: list[Exclusion] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    evaluator_notes: list[EvaluatorNote] = Field(default_factory=list)
    recommender_mode: str  # "llm" or "fallback"
    evaluator_mode: str  # "llm" or "fallback"
    llm_used: bool
