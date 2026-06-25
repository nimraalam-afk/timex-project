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
