/** Lo que el modelo hizo con cada fotograma muestreado. Espejo de bandit.analysis.api.schemas. */

export type ActivityOutcome = "analyzed" | "no_motion" | "over_budget" | "error" | "filtered";

export interface Assessment {
  type: string;
  severity: "low" | "medium" | "high";
  confidence: number;
  description: string;
}

export interface ActivityEntry {
  camera_id: string;
  at: string;
  outcome: ActivityOutcome;
  motion: number;
  assessment: Assessment | null;
  streak: number;
  streak_target: number;
  alerted: boolean;
}

export interface CameraActivity {
  camera_id: string;
  camera_name: string;
  counts: Record<ActivityOutcome, number>;
  has_frame: boolean;
  last_frame_at: string | null;
  recent: ActivityEntry[];
}

export interface ActivitySnapshot {
  model_enabled: boolean;
  /** Modelo en uso; cambia al de respaldo si el principal se queda sin cuota. */
  model?: string | null;
  budget: { used: number; limit: number };
  cameras: CameraActivity[];
}

export interface SyncRun {
  trigger: "startup" | "scheduled" | "manual";
  started_at: string;
  finished_at: string | null;
  published: number;
  rejected: number;
  retired: number;
  completed: boolean;
  error: string | null;
}

export interface SyncStatus {
  running: boolean;
  runs: SyncRun[];
}
