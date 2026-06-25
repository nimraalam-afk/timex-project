# Backend - Timex Scout

FastAPI backend running the scout pipeline. See the [root README](../README.md)
for the full architecture, provider notes, and future work.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /health` -> `{"status": "ok"}`
- `POST /scout/run` -> full `ScoutResult` JSON
- `GET /static/images/...` -> placeholder watch images

## No-API-key fallback check

```bash
unset OPENAI_API_KEY
python3 -c "from app.orchestrator import run_scout; print(run_scout().model_dump_json(indent=2))"
```

Expected: `eligible 35 / excluded 25 / recommended 3`, with `recommender_mode` and
`evaluator_mode` both `"fallback"` and `llm_used: false`.

## Enabling the real OpenAI path

A local `.env` (repo root) is auto-loaded via `python-dotenv`; real environment
variables still take precedence. Set a real key to switch the recommender/evaluator
to the OpenAI Responses API (placeholders like `your_openai_key_here` are ignored):

```bash
export OPENAI_API_KEY=sk-your-real-key   # or uncomment it in .env
python3 -c "from app.orchestrator import run_scout; r = run_scout(); print(r.recommender_mode, r.evaluator_mode, r.llm_used)"
```

With a valid key, expect at least one step to report `llm` and `llm_used: true`.

## Layout

- `app/config.py` - paths, budget rules, OpenAI key detection
- `app/models.py` - Pydantic models (`Listing`, `ScoutResult`, ...)
- `app/providers/` - provider abstraction (`seed_provider.py` default, `live_stubs.py`)
- `app/pipeline/` - `normalize`, `finance`, `validate`, `recommend`, `evaluate`
- `app/orchestrator.py` - wires steps into one traceable result
- `app/main.py` - FastAPI app
- `app/data/` - collector profile, seed listings, reference purchases
