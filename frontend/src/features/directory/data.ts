import type { WantedRecord } from "./types";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

/** Regeneración de respaldo; lo normal es la revalidación tras cada extracción. */
const REVALIDATE_SECONDS = 60;
const IS_BUILD = process.env.NEXT_PHASE === "phase-production-build";

async function read<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${BACKEND_URL}${path}`, {
      next: { revalidate: REVALIDATE_SECONDS },
    });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`El backend respondió ${response.status}`);
    return (await response.json()) as T;
  } catch (error) {
    // En `next build` no hay backend. En ejecución, lanzar el error hace que ISR
    // conserve la última página buena en vez de guardar una vacía.
    if (IS_BUILD) return null;
    throw error;
  }
}

export function fetchDirectory(): Promise<WantedRecord[] | null> {
  return read<WantedRecord[]>("/api/directory");
}

export function fetchWanted(slug: string): Promise<WantedRecord | null> {
  return read<WantedRecord>(`/api/directory/${encodeURIComponent(slug)}`);
}
