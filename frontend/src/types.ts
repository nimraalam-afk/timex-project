// TypeScript mirror of the backend ScoutResult shape (see backend/app/models.py).
// Kept in sync by hand since the API is small.

export interface Recommendation {
  rank: number;
  listing_id: string;
  title: string | null;
  marketplace: string | null;
  listing_url: string | null;
  image_url: string | null;
  total_cad: number;
  why_it_matches: string;
  risk_notes: string[];
}

export interface EvaluatorNote {
  listing_id: string;
  verdict: string; // "ok" or "warn"
  note: string;
}

export interface Exclusion {
  listing_id: string;
  reasons: string[];
}

export interface ScoutResult {
  profile_summary: string;
  counts: Record<string, number>;
  exclusions: Exclusion[];
  recommendations: Recommendation[];
  evaluator_notes: EvaluatorNote[];
  recommender_mode: string;
  evaluator_mode: string;
  llm_used: boolean;
}
