import { api } from "@/lib/api";

export type CameraStatus = "stopped" | "connecting" | "live" | "retrying";

export interface Camera {
  id: string;
  establishment_id: string;
  name: string;
  enabled: boolean;
  status: CameraStatus;
}

export function listCameras(establishmentId: string): Promise<Camera[]> {
  return api(`/api/establishments/${establishmentId}/cameras`);
}

export function createCamera(establishmentId: string, name: string, url: string): Promise<Camera> {
  return api(`/api/establishments/${establishmentId}/cameras`, {
    method: "POST",
    body: JSON.stringify({ name, url }),
  });
}

export function setCameraEnabled(cameraId: string, enabled: boolean): Promise<Camera> {
  return api(`/api/cameras/${cameraId}`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });
}

export function deleteCamera(cameraId: string): Promise<void> {
  return api(`/api/cameras/${cameraId}`, { method: "DELETE" });
}
