"""Thin OpenAI wrapper.

One small helper, `chat_json`, sends a system+user prompt and returns parsed JSON.
We keep the surface tiny on purpose: the recommender and evaluator own the prompts
and the deterministic fallbacks, while this module only handles the API call and
JSON parsing. The OpenAI SDK is imported lazily so the app installs and runs even
if the package or key is absent.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import OPENAI_API_KEY, OPENAI_MODEL, llm_enabled


def chat_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Call OpenAI and return the response parsed as a JSON object.

    Raises if the key is missing or the call/parse fails. Callers are expected to
    check `llm_enabled()` first and to wrap this in a try/except that falls back to
    deterministic logic, so a failure here never breaks a run.
    """
    if not llm_enabled():
        raise RuntimeError("OPENAI_API_KEY not set")

    # Imported here (not at module load) so missing/optional SDK never blocks import.
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        # Ask the model to return strict JSON so we can parse it reliably.
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
