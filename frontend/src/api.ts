// Thin API client for the FastAPI backend.

import type { ScoutResult } from "./types";

// The backend serves both the API and the placeholder images.
export const API_BASE = "http://127.0.0.1:8000";

/** Run the scout pipeline and return the full traceable result. */
export async function runScout(): Promise<ScoutResult> {
  const res = await fetch(`${API_BASE}/scout/run`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/**
 * Resolve a listing image URL. Backend image URLs are relative (e.g.
 * "/static/images/watch-placeholder-5.svg"), so we prefix them with the backend
 * origin to load images from FastAPI rather than the Vite dev server.
 */
export function resolveImageUrl(imageUrl: string | null): string | null {
  if (!imageUrl) return null;
  return imageUrl.startsWith("/") ? `${API_BASE}${imageUrl}` : imageUrl;
}

/** Format a number as CAD currency. */
export function formatCad(amount: number): string {
  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
  }).format(amount);
}
