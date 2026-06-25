// Small summary section: pipeline counts plus a clear "AI run mode" area showing
// the recommender and evaluator steps separately (OpenAI vs deterministic fallback).

import type { ScoutResult } from "../types";

interface Props {
  result: ScoutResult;
}

// Order the counts so the pipeline reads left-to-right.
const COUNT_ORDER = ["raw", "normalized", "eligible", "excluded", "recommended"];

// Human-readable label for a backend mode string ("llm" | "fallback").
function modeLabel(mode: string): string {
  return mode === "llm" ? "OpenAI" : "Deterministic fallback";
}

// One-line explanation so a viewer understands why llm_used can be true even when
// the recommender fell back (the recommender is guarded; the evaluator is separate).
function statusNote(recommender: string, evaluator: string): string {
  const recLlm = recommender === "llm";
  const evalLlm = evaluator === "llm";
  if (recLlm && evalLlm) return "OpenAI generated and evaluated the final picks.";
  if (recLlm && !evalLlm)
    return "OpenAI generated the picks; evaluator used the deterministic fallback.";
  if (!recLlm && evalLlm)
    return "OpenAI evaluated the final picks; recommender used the safe deterministic fallback.";
  return "Both steps used the deterministic fallback (no OpenAI key, or guarded fallback).";
}

function StepPill({ label, mode }: { label: string; mode: string }) {
  const isLlm = mode === "llm";
  return (
    <div className="step">
      <span className="step-label">{label}</span>
      <span className={`pill ${isLlm ? "pill-openai" : "pill-fallback"}`}>{modeLabel(mode)}</span>
    </div>
  );
}

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

      <div className="aistatus">
        <span className="aistatus-title">AI run mode</span>
        <div className="aistatus-steps">
          <StepPill label="Recommender" mode={result.recommender_mode} />
          <StepPill label="Evaluator" mode={result.evaluator_mode} />
        </div>
        <p className="aistatus-note">{statusNote(result.recommender_mode, result.evaluator_mode)}</p>
      </div>
    </section>
  );
}
