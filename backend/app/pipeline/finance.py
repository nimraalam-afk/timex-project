"""Financial math: deterministic landed-cost calculation in integer cents.

Money is never handed to the LLM. We compute total landed cost (item + shipping,
converted to CAD) using integer cents to avoid floating-point drift, then compare
against the hard budget limit. The result is a transparent breakdown the UI can
show line by line.

Convention (matches the seed data): convert the summed item+shipping amount to
CAD with the listing's FX rate, then round once to the nearest cent.
"""

from __future__ import annotations

from typing import Optional

from app.config import BUDGET_LIMIT_CENTS
from app.models import FinanceBreakdown, Listing


def _to_cents(amount: float) -> int:
    """Round a currency amount to integer cents (half-up via round())."""
    return round(amount * 100)


def compute_landed_cost(listing: Listing) -> FinanceBreakdown:
    """Compute the CAD landed cost for a listing.

    Raises ValueError when required money fields are missing, so validation can
    report it as a clear rejection reason instead of guessing at a price.
    """
    if listing.price is None or listing.shipping is None or listing.fx_rate_to_cad is None:
        raise ValueError("missing price, shipping, or fx_rate_to_cad")

    item_cents = _to_cents(listing.price)
    shipping_cents = _to_cents(listing.shipping)

    # Sum in the source currency first, then convert once to CAD.
    source_total_cents = item_cents + shipping_cents
    total_cad_cents = round(source_total_cents * listing.fx_rate_to_cad)

    return FinanceBreakdown(
        item_cents=item_cents,
        shipping_cents=shipping_cents,
        fx_rate_to_cad=listing.fx_rate_to_cad,
        total_cad_cents=total_cad_cents,
        within_budget=total_cad_cents <= BUDGET_LIMIT_CENTS,
    )


def safe_finance(listing: Listing) -> Optional[FinanceBreakdown]:
    """Like `compute_landed_cost`, but returns None instead of raising.

    Convenience for validation, which wants to record a missing-money rejection
    rather than handle an exception.
    """
    try:
        return compute_landed_cost(listing)
    except ValueError:
        return None
