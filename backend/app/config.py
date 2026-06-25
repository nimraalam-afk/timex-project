"""Central configuration: file paths, budget rules, and OpenAI key detection.

Everything here is deterministic and import-safe. We keep config in one place so
the pipeline modules never hardcode paths or magic numbers, which makes the flow
easy to explain and adjust during a walkthrough.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load a local .env for development. `override=False` keeps real environment
# variables authoritative (the .env only fills in values that are not already set).
# find_dotenv (the default) walks up from this file, so the repo-root .env is found
# regardless of the current working directory.
load_dotenv(override=False)

# --- Filesystem paths -------------------------------------------------------
# Resolve paths relative to this file so the app runs from any working directory.
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
STATIC_DIR = APP_DIR / "static"

SEED_LISTINGS_PATH = DATA_DIR / "seed_listings.normalized.json"
REFERENCE_PURCHASES_PATH = DATA_DIR / "reference_purchases.normalized.json"
COLLECTOR_PROFILE_PATH = DATA_DIR / "collector_profile.json"

# --- Budget rules (hard constraints) ----------------------------------------
# The collector's budget is a hard constraint: total landed cost (item + shipping
# converted to CAD) must be at or under this limit. We store it as integer cents
# so all money math can stay in integers and avoid floating-point drift.
BUDGET_LIMIT_CAD = 50.0
BUDGET_LIMIT_CENTS = 5000
SHIPS_TO_POSTAL_CODE = "M6K1V8"

# Brand the collector cares about. Used as a deterministic hard filter.
REQUIRED_BRAND = "Timex"

# Marketplaces we treat as known/trusted sources during validation.
KNOWN_MARKETPLACES = {"eBay", "Etsy", "Chrono24"}

# --- Listing source / eBay provider ----------------------------------------
# Which provider feeds the pipeline. "seed" (default) uses the bundled, reliable
# seed data; "ebay" opts in to the live eBay Browse API provider. Anything that
# is not exactly "ebay" keeps the safe seed default.
LISTING_SOURCE = os.getenv("LISTING_SOURCE", "seed").strip().lower()

# eBay OAuth client credentials (App ID / Cert ID). Empty/placeholder values
# mean the eBay path stays disabled and the pipeline keeps using seed data.
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")

# "production" (default) or "sandbox" - selects the OAuth and Browse base URLs.
EBAY_ENV = os.getenv("EBAY_ENV", "production").strip().lower() or "production"

# Marketplace + buyer context. Defaults target Canada so landed-cost and FX
# assumptions line up with the collector profile (ships to M6K1V8).
EBAY_MARKETPLACE_ID = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_CA")
EBAY_BUYER_COUNTRY = os.getenv("EBAY_BUYER_COUNTRY", "CA")
EBAY_BUYER_POSTAL_CODE = os.getenv("EBAY_BUYER_POSTAL_CODE", SHIPS_TO_POSTAL_CODE)


def _clamp_result_limit(raw: str | None, default: int = 30) -> int:
    """Parse EBAY_RESULT_LIMIT and clamp to a safe 1-50 range.

    Bad/empty values fall back to the default so a typo in .env never breaks
    the run or asks eBay for an unreasonable page size.
    """
    try:
        value = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        value = default
    return max(1, min(50, value))


# Candidate pool size requested from eBay; kept small and bounded for the MVP.
EBAY_RESULT_LIMIT = _clamp_result_limit(os.getenv("EBAY_RESULT_LIMIT"))

# Values that look configured but are not real eBay credentials. Treated as
# disabled so copying .env.example never accidentally enables the eBay path.
_EBAY_PLACEHOLDER_VALUES = {
    "",
    "your_ebay_client_id_here",
    "your_ebay_client_secret_here",
    "changeme",
}


def ebay_enabled() -> bool:
    """True only when both eBay credentials look real (not placeholders).

    Mirrors `llm_enabled()`: empty values and obvious placeholders count as
    disabled so the orchestrator cleanly falls back to the seed provider.
    """
    client_id = (EBAY_CLIENT_ID or "").strip()
    client_secret = (EBAY_CLIENT_SECRET or "").strip()
    if client_id.lower() in _EBAY_PLACEHOLDER_VALUES:
        return False
    if client_secret.lower() in _EBAY_PLACEHOLDER_VALUES:
        return False
    return True


# --- LLM configuration ------------------------------------------------------
# The recommender and evaluator use OpenAI when a key is present, and fall back
# to deterministic logic otherwise so the seed demo always works.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Values that look configured but are not real keys. If the key matches one of
# these (case-insensitive, trimmed), we treat OpenAI as disabled so copying
# .env.example or leaving a placeholder never accidentally enables the LLM path.
_PLACEHOLDER_KEYS = {"", "your_openai_key_here", "sk-...", "changeme"}


def llm_enabled() -> bool:
    """True only when a real-looking OpenAI key is configured.

    Empty values and obvious placeholders count as disabled, so callers cleanly
    fall back to deterministic logic.
    """
    key = (OPENAI_API_KEY or "").strip()
    return key.lower() not in _PLACEHOLDER_KEYS
