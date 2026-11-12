/** Prueba de rostros. Espejo de bandit.faces.api.schemas. */

export type FaceOutcome = "match" | "no_match" | "no_face" | "error";

export interface FaceCheck {
  id: string;
  camera_id: string;
  camera_name: string;
  at: string;
  outcome: FaceOutcome;
  person: string | null;
  confidence: number;
  explanation: string;
  alerted: boolean;
}

export interface FaceWatch {
  enabled: boolean;
  model: string | null;
  people: string[];
  used: number;
  limit: number;
  counts: Record<FaceOutcome, number>;
  recent: FaceCheck[];
}
