# Frontend - Timex Scout

Thin Vite + React + TypeScript single-screen UI. See the
[root README](../README.md) for the full architecture.

## Run

Requires Node.js 18+. Start the backend on port 8000 first.

```bash
npm install
npm run dev
```

Open the printed URL (default http://localhost:5173) and click **Run watch search**.

## What it shows

- A summary bar: pipeline counts plus `recommender_mode`, `evaluator_mode`, `llm_used`.
- The top three recommendation cards: rank, image, title, marketplace, total CAD,
  why it matches, risk notes, the evaluator verdict/note, and a listing link.

## Notes

- The backend base URL is set in `src/api.ts` (`API_BASE = http://127.0.0.1:8000`).
- Listing image URLs are relative (e.g. `/static/images/...`); `resolveImageUrl`
  prefixes them with the backend origin so images load from FastAPI.
