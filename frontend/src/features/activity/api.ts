import type { WantedRecord } from "@/features/directory/types";
import { api } from "@/lib/api";
import { cached, invalidate } from "@/lib/cache";
import type { ActivitySnapshot, SyncStatus } from "./types";

export function getActivity(establishmentId: string): Promise<ActivitySnapshot> {
  return api<ActivitySnapshot>(`/api/establishments/${establishmentId}/analysis-activity`);
}

/** El parámetro cambia con cada análisis para que el navegador pida el fotograma nuevo. */
export function lastFrameUrl(cameraId: string, version: string): string {
  return `/api/analysis/cameras/${cameraId}/last-frame?v=${encodeURIComponent(version)}`;
}

const DIRECTORY = "directory";
const DIRECTORY_MAX_AGE_MS = 5 * 60_000;

/** El directorio cambia solo al sincronizar: se reutiliza unos minutos entre ventanas. */
export function listWanted(fresh = false): Promise<WantedRecord[]> {
  if (fresh) invalidate(DIRECTORY);
  return cached(DIRECTORY, () => api<WantedRecord[]>("/api/directory"), DIRECTORY_MAX_AGE_MS);
}

export function getSyncStatus(): Promise<SyncStatus> {
  return api<SyncStatus>("/api/directory/sync-runs");
}

export function startSync(): Promise<SyncStatus> {
  return api<SyncStatus>("/api/directory/sync", { method: "POST" });
}
