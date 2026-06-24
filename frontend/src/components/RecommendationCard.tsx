// One recommendation card: rank, image, title, budget, reasoning, risks, and
// the evaluator's verdict for this listing.

import { formatCad, resolveImageUrl } from "../api";
import type { EvaluatorNote, Recommendation } from "../types";

interface Props {
  rec: Recommendation;
  evaluation?: EvaluatorNote;
}

export function RecommendationCard({ rec, evaluation }: Props) {
  const image = resolveImageUrl(rec.image_url);

  return (
    <article className="card">
      <div className="card-rank">#{rec.rank}</div>

      {image && <img className="card-image" src={image} alt={rec.title ?? "watch"} />}

      <div className="card-body">
        <h3 className="card-title">{rec.title ?? rec.listing_id}</h3>
        <div className="card-meta">
          {rec.marketplace && <span className="chip">{rec.marketplace}</span>}
          <span className="chip chip-price">{formatCad(rec.total_cad)}</span>
        </div>

        <p className="card-why">{rec.why_it_matches}</p>

        {rec.risk_notes.length > 0 && (
          <div className="card-section">
            <span className="card-section-label">Risk notes</span>
            <ul className="risk-list">
              {rec.risk_notes.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {evaluation && (
          <div className={`evaluator evaluator-${evaluation.verdict}`}>
            <strong>Evaluator: {evaluation.verdict.toUpperCase()}</strong>
            <span> — {evaluation.note}</span>
          </div>
        )}

        {rec.listing_url && (
          <a className="card-link" href={rec.listing_url} target="_blank" rel="noreferrer">
            View listing
          </a>
        )}
      </div>
    </article>
  );
}
