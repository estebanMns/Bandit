import type { WantedRecord } from "@/features/directory/types";
import { api } from "@/lib/api";
import type { ActivitySnapshot, SyncStatus } from "./types";

export function getActivity(establishmentId: string): Promise<ActivitySnapshot> {
  return api<ActivitySnapshot>(`/api/establishments/${establishmentId}/analysis-activity`);
}

/** El parámetro cambia con cada análisis para que el navegador pida el fotograma nuevo. */
export function lastFrameUrl(cameraId: string, version: string): string {
  return `/api/analysis/cameras/${cameraId}/last-frame?v=${encodeURIComponent(version)}`;
}

export function listWanted(): Promise<WantedRecord[]> {
  return api<WantedRecord[]>("/api/directory");
}

export function getSyncStatus(): Promise<SyncStatus> {
  return api<SyncStatus>("/api/directory/sync-runs");
}

export function startSync(): Promise<SyncStatus> {
  return api<SyncStatus>("/api/directory/sync", { method: "POST" });
}
