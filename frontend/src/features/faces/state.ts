import type { FaceCheck, FaceOutcome, FaceWatch } from "./types";

export const RECENT_LIMIT = 40;

export const OUTCOME_LABELS: Record<FaceOutcome, string> = {
  match: "Coincide",
  no_match: "No coincide",
  no_face: "Sin cara visible",
  error: "Falló la consulta",
};

/** Suma una comparación que llegó en vivo, sin repetirla si ya estaba. */
export function applyCheck(watch: FaceWatch, check: FaceCheck): FaceWatch {
  if (watch.recent.some((item) => item.id === check.id)) return watch;
  return {
    ...watch,
    used: watch.used + 1,
    counts: { ...watch.counts, [check.outcome]: (watch.counts[check.outcome] ?? 0) + 1 },
    recent: [check, ...watch.recent].slice(0, RECENT_LIMIT),
  };
}

/** Caras comparadas: lo que cuenta para medir aciertos, sin imágenes vacías ni fallas. */
export function comparedFaces(watch: FaceWatch): number {
  return watch.counts.match + watch.counts.no_match;
}
