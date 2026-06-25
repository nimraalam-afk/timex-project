"""Live eBay Browse API provider (opt-in).

This is the smallest safe live integration behind the provider seam. It only
runs when `LISTING_SOURCE=ebay` and real eBay credentials are present; the
orchestrator falls back to `SeedProvider` on any failure, so the demo never
depends on eBay being reachable.

Design notes:
- We keep retrieval broad (a keyword search) and do NOT encode collector taste
  here; the deterministic pipeline still owns all hard rules and judgment.
- `fetch_raw` returns dicts already shaped like the normalized `Listing` schema
  (same as the seed data), so `normalize.py` needs no changes.
- Money fields are mapped conservatively: missing shipping or non-CAD currency
  is left as `None`/unmapped so deterministic validation rejects the listing
  rather than inventing a price or FX rate.
"""

from __future__ import annotations

import base64
from typing import Any, Optional

import httpx

from app import config
from app.providers.base import ListingProvider

# OAuth token endpoints (client credentials grant) per environment.
_TOKEN_URLS = {
    "production": "https://api.ebay.com/identity/v1/oauth2/token",
    "sandbox": "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
}

# Browse API base URLs per environment.
_BROWSE_BASES = {
    "production": "https://api.ebay.com",
    "sandbox": "https://api.sandbox.ebay.com",
}

# Browse application scope; sufficient for item_summary/search.
_OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"
_SEARCH_PATH = "/buy/browse/v1/item_summary/search"

# Short timeout so a slow eBay response cannot stall the demo; failures fall
# back to seed in the orchestrator.
_HTTP_TIMEOUT = 10.0


class EbayProvider(ListingProvider):
    """Fetches Timex listings from the eBay Browse API.

    Any token, network, rate-limit, HTTP, or mapping failure raises, which the
    orchestrator catches to fall back to the seed provider.
    """

    name = "ebay"

    def _env(self) -> str:
        """Return the configured environment, defaulting to production."""
        return config.EBAY_ENV if config.EBAY_ENV in _TOKEN_URLS else "production"

    def _get_token(self) -> str:
        """Run the OAuth client-credentials flow and return an access token.

        Raises on any non-200 response so the caller can fall back cleanly.
        """
        token_url = _TOKEN_URLS[self._env()]

        # Basic auth header is base64("client_id:client_secret").
        raw_auth = f"{config.EBAY_CLIENT_ID}:{config.EBAY_CLIENT_SECRET}".encode("utf-8")
        basic = base64.b64encode(raw_auth).decode("ascii")

        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        body = {
            "grant_type": "client_credentials",
            "scope": _OAUTH_SCOPE,
        }

        resp = httpx.post(token_url, headers=headers, data=body, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise ValueError("eBay token response missing access_token")
        return token

    def _search(self, token: str, query: str) -> list[dict[str, Any]]:
        """Call Browse item_summary/search and return the raw itemSummaries list."""
        base = _BROWSE_BASES[self._env()]

        # Contextual location helps eBay return buyer-relevant shipping/availability.
        end_user_ctx = (
            f"contextualLocation=country%3D{config.EBAY_BUYER_COUNTRY}"
            f"%2Czip%3D{config.EBAY_BUYER_POSTAL_CODE}"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": config.EBAY_MARKETPLACE_ID,
            "X-EBAY-C-ENDUSERCTX": end_user_ctx,
            "Accept-Language": "en-CA",
        }
        params = {
            "q": query,
            "limit": config.EBAY_RESULT_LIMIT,
        }

        resp = httpx.get(
            f"{base}{_SEARCH_PATH}",
            headers=headers,
            params=params,
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("itemSummaries", []) or []

    def fetch_raw(self, query: str = "Timex watch") -> list[dict[str, Any]]:
        """Return a bounded pool of normalized-shaped listing dicts from eBay.

        Per-item mapping problems skip just that item; a token/search failure or
        an unexpected top-level error propagates so the orchestrator falls back
        to seed data.
        """
        token = self._get_token()
        summaries = self._search(token, query)

        mapped: list[dict[str, Any]] = []
        for summary in summaries:
            try:
                record = _map_item(summary)
            except Exception:
                # One bad item should not sink the whole batch.
                continue
            if record is None:
                continue
            # Prefer fixed-price items only (Browse defaults to fixed price, but
            # post-filter to be explicit and avoid auctions sneaking in).
            buying_options = summary.get("buyingOptions") or []
            if "FIXED_PRICE" not in buying_options:
                continue
            mapped.append(record)

        # Keep the candidate pool bounded to the configured limit.
        return mapped[: config.EBAY_RESULT_LIMIT]


# --- Mapping helpers --------------------------------------------------------
# Keyword hints used only to set `is_watch`; broad on purpose. Hard rules stay
# in the deterministic validation step, not here.
_WATCH_HINTS = ("watch", "wristwatch", "wrist watch")


def _to_float(value: Any) -> Optional[float]:
    """Best-effort numeric coercion; returns None when not parseable."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _looks_like_watch(title: Optional[str], categories: list[dict[str, Any]]) -> bool:
    """True if the title or category names suggest an actual watch."""
    haystack = (title or "").lower()
    for cat in categories:
        name = (cat.get("categoryName") or "").lower()
        haystack += f" {name}"
    return any(hint in haystack for hint in _WATCH_HINTS)


def _map_item(summary: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Map one eBay item summary into a normalized `Listing`-shaped dict.

    Returns None for items we cannot meaningfully identify (no itemId). Money
    fields are mapped conservatively so validation, not this mapper, decides
    eligibility.
    """
    item_id = summary.get("itemId")
    if not item_id:
        return None

    title = summary.get("title")
    title_text = title or ""

    # Price: numeric value if present, plus its currency.
    price_obj = summary.get("price") or {}
    price = _to_float(price_obj.get("value"))
    currency = price_obj.get("currency")

    # Shipping: first option's cost if present; otherwise leave None so
    # validation rejects rather than assuming free shipping.
    shipping: Optional[float] = None
    shipping_options = summary.get("shippingOptions") or []
    if shipping_options:
        cost = (shipping_options[0] or {}).get("shippingCost") or {}
        shipping = _to_float(cost.get("value"))

    # FX: only assert 1.0 when the listing is already in CAD. Otherwise leave
    # None so the deterministic step rejects instead of inventing a rate.
    fx_rate_to_cad: Optional[float] = 1.0 if currency == "CAD" else None

    # Seller signals (mapped to the existing Listing field names).
    seller = summary.get("seller") or {}
    seller_name = seller.get("username")
    seller_feedback_count = seller.get("feedbackScore")
    seller_positive_feedback_percent = _to_float(seller.get("feedbackPercentage"))

    categories = summary.get("categories") or []

    # Surface money-related caution as a risk flag (non-blocking signal).
    risk_flags: list[str] = []
    if shipping is None:
        risk_flags.append("shipping cost missing")
    if currency and currency != "CAD":
        risk_flags.append(f"non-CAD currency: {currency}")

    item_web_url = summary.get("itemWebUrl")
    image_url = (summary.get("image") or {}).get("imageUrl")

    return {
        "id": f"ebay-{item_id}",
        "record_type": "candidate_listing",
        "brand": "Timex" if "timex" in title_text.lower() else None,
        "title": title,
        "marketplace": "eBay",
        "source_type": "live_api",
        "source_url": item_web_url,
        "listing_url": item_web_url,
        "image_url": image_url,
        "availability_state": "active",
        "is_watch": _looks_like_watch(title, categories),
        "price": price,
        "shipping": shipping,
        "currency": currency,
        "fx_rate_to_cad": fx_rate_to_cad,
        "condition": summary.get("condition"),
        "description": summary.get("shortDescription") or title,
        "risk_flags": risk_flags,
        "seller_name": seller_name,
        "seller_feedback_count": seller_feedback_count,
        "seller_positive_feedback_percent": seller_positive_feedback_percent,
        "seller_location": (summary.get("itemLocation") or {}).get("country"),
        # Preserve the raw eBay summary for traceability/debugging.
        "item_details": summary,
    }
