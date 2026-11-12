import { api } from "@/lib/api";
import type { FaceWatch } from "./types";

export function getFaceWatch(establishmentId: string): Promise<FaceWatch> {
  return api<FaceWatch>(`/api/establishments/${establishmentId}/face-checks`);
}

export function faceFrameUrl(checkId: string): string {
  return `/api/face-checks/${checkId}/frame`;
}
