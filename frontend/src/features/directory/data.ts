import type { WantedRecord } from "./types";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

/** Regeneración de respaldo; lo normal es la revalidación tras cada extracción. */
export const REVALIDATE_SECONDS = 3600;

async function read<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${BACKEND_URL}${path}`, {
      next: { revalidate: REVALIDATE_SECONDS },
    });
    return response.ok ? ((await response.json()) as T) : null;
  } catch {
    // Sin backend (como en `next build`) la página avisa y se regenera después.
    return null;
  }
}

export function fetchDirectory(): Promise<WantedRecord[] | null> {
  return read<WantedRecord[]>("/api/directory");
}

export function fetchWanted(slug: string): Promise<WantedRecord | null> {
  return read<WantedRecord>(`/api/directory/${encodeURIComponent(slug)}`);
}
