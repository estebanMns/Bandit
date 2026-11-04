import type { Incident } from "@/features/incidents/types";

/** Mensajes del backend por /ws/events. */
export type ServerEvent =
  | { type: "sync" }
  | { type: "incident"; incident: Incident }
  | { type: "camera"; cameraId: string; status: string };

export type ToSharedWorker =
  | { type: "join"; establishmentId: string }
  | { type: "leave" };

export type FromSharedWorker =
  | ServerEvent
  | { type: "connection"; connected: boolean; tabs: number };
