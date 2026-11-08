import type { ActivityEntry, ActivityOutcome, ActivitySnapshot, CameraActivity } from "./types";

export const RECENT_LIMIT = 50;

/** Resultados que gastan una consulta del presupuesto diario. */
const SPENDS_BUDGET: ReadonlySet<ActivityOutcome> = new Set(["analyzed", "error", "filtered"]);

const EMPTY_COUNTS: Record<ActivityOutcome, number> = {
  analyzed: 0,
  no_motion: 0,
  over_budget: 0,
  error: 0,
  filtered: 0,
};

function emptyCamera(entry: ActivityEntry, name: string): CameraActivity {
  return {
    camera_id: entry.camera_id,
    camera_name: name,
    counts: { ...EMPTY_COUNTS },
    has_frame: false,
    last_frame_at: null,
    recent: [],
  };
}

/** Aplica un mensaje en vivo sin mutar el estado. Ignora repetidos y mensajes viejos. */
export function applyEntry(
  snapshot: ActivitySnapshot,
  cameraName: string,
  entry: ActivityEntry,
): ActivitySnapshot {
  const existing = snapshot.cameras.find((camera) => camera.camera_id === entry.camera_id);
  const camera = existing ?? emptyCamera(entry, cameraName);
  const newest = camera.recent[0];
  if (newest && newest.at >= entry.at) return snapshot;

  const withFrame = entry.outcome !== "no_motion" && entry.outcome !== "over_budget";
  const updated: CameraActivity = {
    ...camera,
    camera_name: cameraName,
    counts: { ...camera.counts, [entry.outcome]: camera.counts[entry.outcome] + 1 },
    has_frame: camera.has_frame || withFrame,
    last_frame_at: withFrame ? entry.at : camera.last_frame_at,
    recent: [entry, ...camera.recent].slice(0, RECENT_LIMIT),
  };
  const cameras = existing
    ? snapshot.cameras.map((item) => (item.camera_id === entry.camera_id ? updated : item))
    : [...snapshot.cameras, updated].sort((a, b) => a.camera_name.localeCompare(b.camera_name));
  const spent = SPENDS_BUDGET.has(entry.outcome) ? 1 : 0;

  return {
    ...snapshot,
    budget: { ...snapshot.budget, used: snapshot.budget.used + spent },
    cameras,
  };
}

/** Todas las evaluaciones de todas las cámaras, de la más reciente a la más antigua. */
export function timeline(snapshot: ActivitySnapshot, limit = 30): (ActivityEntry & { camera_name: string })[] {
  return snapshot.cameras
    .flatMap((camera) => camera.recent.map((entry) => ({ ...entry, camera_name: camera.camera_name })))
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, limit);
}
