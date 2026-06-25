"""Evaluator: a lightweight quality gate over the top recommendations.

It is intentionally small - not a metrics framework. It checks that each
recommendation is faithful to its listing, clearly respects budget/condition, and
does not quietly ignore a risk signal. Like the recommender, it uses the LLM when
available and a deterministic fallback otherwise, returning identical output.
"""

from __future__ import annotations

import json
import logging

from app.config import llm_enabled
from app.llm.client import chat_json
from app.models import Candidate, EvaluatorNote, Recommendation

logger = logging.getLogger(__name__)


def _sanitized(exc: Exception) -> str:
    """Concise, safe summary of an exception for logging.

    Only the exception class name and a truncated message - never tracebacks,
    payloads, headers, env vars, or secrets.
    """
    return f"{type(exc).__name__}: {str(exc)[:200]}"


# Risk words serious enough that the evaluator wants the user explicitly warned.
NOTABLE_RISK_WORDS = ("untested", "as-is", "as is", "unknown", "dead battery", "unverified")


def evaluate(
    recommendations: list[Recommendation],
    candidates: list[Candidate],
    profile: dict,
) -> tuple[list[EvaluatorNote], str]:
    """Return (notes, mode) where mode is "llm" or "fallback"."""
    if not recommendations:
        return [], "fallback"

    by_id = {c.listing.id: c for c in candidates}
    if llm_enabled():
        try:
            return _evaluate_llm(recommendations, by_id, profile), "llm"
        except Exception as exc:
            logger.warning("LLM evaluator failed; using fallback: %s", _sanitized(exc))
    return _evaluate_fallback(recommendations, by_id), "fallback"


# --- Deterministic fallback -------------------------------------------------

def _evaluate_fallback(
    recommendations: list[Recommendation], by_id: dict[str, Candidate]
) -> list[EvaluatorNote]:
    notes: list[EvaluatorNote] = []
    for rec in recommendations:
        candidate = by_id.get(rec.listing_id)
        concerns: list[str] = []

        if candidate is not None:
            # Budget must hold (defensive; validation already guaranteed it).
            if not candidate.finance.within_budget:
                concerns.append("total cost exceeds budget")
            # A risk flag on the listing should be surfaced to the user.
            if candidate.risk_flags and not rec.risk_notes:
                concerns.append("listing has risk flags not surfaced in the recommendation")
            # Call out notable caution signals explicitly.
            flags_text = " ".join(candidate.risk_flags).lower()
            if any(word in flags_text for word in NOTABLE_RISK_WORDS):
                concerns.append("notable condition risk; confirm details before buying")

        verdict = "warn" if concerns else "ok"
        note = "; ".join(concerns) if concerns else "Within budget, working, and risks surfaced."
        notes.append(EvaluatorNote(listing_id=rec.listing_id, verdict=verdict, note=note))
    return notes


# --- LLM path ---------------------------------------------------------------

def _evaluate_llm(
    recommendations: list[Recommendation],
    by_id: dict[str, Candidate],
    profile: dict,
) -> list[EvaluatorNote]:
    system = (
        "You are a careful reviewer of watch buying recommendations. For each recommendation, "
        "check that it is faithful to the listing data, respects the budget and condition rules, "
        "and does not ignore a risk signal. Be concise. Return strict JSON."
    )
    payload = {
        "instruction": (
            'For each recommendation return listing_id, verdict ("ok" or "warn"), and a short note. '
            'Respond as {"notes": [...]}.'
        ),
        "collector_profile": profile,
        "recommendations": [
            {
                "listing_id": r.listing_id,
                "why_it_matches": r.why_it_matches,
                "risk_notes": r.risk_notes,
                "total_cad": r.total_cad,
                # Include the source listing fields so the model can check faithfulness.
                "listing": by_id[r.listing_id].listing.model_dump(
                    include={"title", "condition", "working_status", "description", "style_tags"}
                )
                if r.listing_id in by_id
                else {},
            }
            for r in recommendations
        ],
    }

    data = chat_json(system, json.dumps(payload))
    valid_ids = {r.listing_id for r in recommendations}
    notes: list[EvaluatorNote] = []
    for item in data.get("notes", []):
        lid = item.get("listing_id")
        if lid not in valid_ids:
            continue
        verdict = "warn" if item.get("verdict") == "warn" else "ok"
        notes.append(EvaluatorNote(listing_id=lid, verdict=verdict, note=item.get("note", "")))
    if not notes:
        raise ValueError("LLM returned no valid evaluator notes")
    return notes
