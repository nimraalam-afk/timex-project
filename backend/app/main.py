"""FastAPI app: the thin HTTP layer over the orchestrator.

Two endpoints (health + run the scout) plus a static mount for placeholder watch
images. All the real work lives in the pipeline/orchestrator; this file only wires
HTTP to `run_scout()` and returns the traceable `ScoutResult` as JSON.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR
from app.models import ScoutResult
from app.orchestrator import run_scout

app = FastAPI(title="Timex Scout MVP")

# Permissive CORS so the local React frontend (built later) can call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve placeholder watch images referenced by listings' image_url (/static/images/...).
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check."""
    return {"status": "ok"}


@app.post("/scout/run", response_model=ScoutResult)
def scout_run() -> ScoutResult:
    """Run the full scout pipeline and return the traceable result.

    Uses the seed provider and works with no OPENAI_API_KEY (the recommender and
    evaluator fall back to deterministic logic).
    """
    return run_scout()
