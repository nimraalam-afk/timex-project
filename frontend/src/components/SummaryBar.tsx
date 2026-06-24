// Small summary section: pipeline counts and which path (LLM vs fallback) ran.

import type { ScoutResult } from "../types";

interface Props {
  result: ScoutResult;
}

// Order the counts so the pipeline reads left-to-right.
const COUNT_ORDER = ["raw", "normalized", "eligible", "excluded", "recommended"];

export function SummaryBar({ result }: Props) {
  return (
    <section className="summary">
      <div className="summary-counts">
        {COUNT_ORDER.filter((k) => k in result.counts).map((key) => (
          <div className="stat" key={key}>
            <span className="stat-value">{result.counts[key]}</span>
            <span className="stat-label">{key}</span>
          </div>
        ))}
      </div>
      <div className="summary-modes">
        <span className="badge">recommender: {result.recommender_mode}</span>
        <span className="badge">evaluator: {result.evaluator_mode}</span>
        <span className={`badge ${result.llm_used ? "badge-on" : "badge-off"}`}>
          llm_used: {String(result.llm_used)}
        </span>
      </div>
    </section>
  );
}
