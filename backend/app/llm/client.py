"""Thin OpenAI wrapper.

One small helper, `chat_json`, sends a system+user prompt and returns parsed JSON.
We keep the surface tiny on purpose: the recommender and evaluator own the prompts
and the deterministic fallbacks, while this module only handles the API call and
JSON parsing.

This uses the current OpenAI SDK style (`OpenAI()` + the Responses API). The model
is taken from config (never hard-coded here). Errors are raised with clear messages
and NOT swallowed: callers already wrap this in a try/except that falls back to
deterministic logic, so a failure here never breaks a run.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import OPENAI_API_KEY, OPENAI_MODEL, llm_enabled


def chat_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Call OpenAI via the Responses API and return the reply parsed as JSON.

    Raises:
        RuntimeError: if no usable key is configured.
        Exception:    if the API call fails (SDK error is propagated).
        ValueError:   if the response text is not valid JSON.
    """
    if not llm_enabled():
        raise RuntimeError("OpenAI key missing or placeholder; cannot call the API")

    # Imported here (not at module load) so the optional SDK never blocks import.
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Responses API: pass system+user as input messages and request strict JSON via
    # `text.format` (verified against the installed SDK: openai 2.x uses `text`,
    # not `response_format`). The prompts also instruct JSON as a backstop.
    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text={"format": {"type": "json_object"}},
        temperature=0.2,
    )

    # `output_text` is the SDK's convenience accessor for the aggregated text output.
    text = (response.output_text or "").strip() or "{}"
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI response was not valid JSON: {exc}") from exc
