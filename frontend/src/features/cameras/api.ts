import { api } from "@/lib/api";

export type CameraStatus = "stopped" | "connecting" | "live" | "retrying";

export interface Camera {
  id: string;
  establishment_id: string;
  name: string;
  enabled: boolean;
  status: CameraStatus;
  /** Por qué no hay video, si el backend lo sabe (nunca trae la URL ni la clave). */
  problem?: string | null;
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

export interface DiscoveredDevice {
  ip: string;
  open_ports: number[];
  brand: string | null;
  rtsp_server: string | null;
  http_server: string | null;
  looks_like_camera: boolean;
}

export type ConnectOutcome = "connected" | "wrong_password" | "unreachable" | "not_found";

export interface WorkingStream {
  path: string;
  label: string;
  source: "conocida" | "ia";
}

export interface ConnectResult {
  outcome: ConnectOutcome;
  port: number;
  tried: number;
  ai_used: boolean;
  streams: WorkingStream[];
}

export function scanNetwork(establishmentId: string, network: string): Promise<DiscoveredDevice[]> {
  return api(`/api/establishments/${establishmentId}/camera-scan`, {
    method: "POST",
    body: JSON.stringify({ network }),
  });
}

export function connectDevice(
  establishmentId: string,
  ip: string,
  username: string,
  password: string,
): Promise<ConnectResult> {
  return api(`/api/establishments/${establishmentId}/camera-scan/connect`, {
    method: "POST",
    body: JSON.stringify({ ip, username, password }),
  });
}

/** La URL se arma en el navegador: la clave nunca vuelve del servidor. */
export function streamUrl(
  ip: string,
  port: number,
  path: string,
  username: string,
  password: string,
) {
  const credentials = `${encodeURIComponent(username)}:${encodeURIComponent(password)}`;
  return `rtsp://${credentials}@${ip}:${port}${path}`;
}

export interface ConnectionAttempt {
  method: "red_local" | "nube_imou";
  status: string;
  detail: string;
}

export interface AutoConnectResult {
  connected: boolean;
  added: string[];
  already: number;
  attempts: ConnectionAttempt[];
}

export function autoConnect(
  establishmentId: string,
  network: string | null,
  username: string,
  password: string,
): Promise<AutoConnectResult> {
  return api(`/api/establishments/${establishmentId}/cameras/auto-connect`, {
    method: "POST",
    body: JSON.stringify({ network, username, password }),
  });
}

export function connectionOptions(): Promise<{ imou_cloud: boolean }> {
  return api("/api/cameras/connection-options");
}
