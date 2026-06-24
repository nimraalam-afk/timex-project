// Single-screen Timex Scout UI: run the search, then show a summary and the
// top-3 recommendation cards.

import { useState } from "react";
import { runScout } from "./api";
import { RecommendationCard } from "./components/RecommendationCard";
import { SummaryBar } from "./components/SummaryBar";
import type { EvaluatorNote, ScoutResult } from "./types";

export default function App() {
  const [result, setResult] = useState<ScoutResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      setResult(await runScout());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  // Index evaluator notes by listing id so each card can show its own verdict.
  const notesById: Record<string, EvaluatorNote> = {};
  result?.evaluator_notes.forEach((n) => (notesById[n.listing_id] = n));

  return (
    <div className="page">
      <header className="header">
        <h1>Timex Scout</h1>
        <p className="subtitle">
          Surface the best current vintage Timex listings under $50 CAD all-in.
        </p>
        <button className="run-button" onClick={handleRun} disabled={loading}>
          {loading ? "Searching…" : "Run watch search"}
        </button>
      </header>

      {error && <div className="error">{error}</div>}

      {result && (
        <main className="results">
          {result.profile_summary && <p className="profile">{result.profile_summary}</p>}

          <SummaryBar result={result} />

          <h2 className="section-heading">Top recommendations</h2>
          <div className="cards">
            {result.recommendations.map((rec) => (
              <RecommendationCard
                key={rec.listing_id}
                rec={rec}
                evaluation={notesById[rec.listing_id]}
              />
            ))}
          </div>
        </main>
      )}
    </div>
  );
}
