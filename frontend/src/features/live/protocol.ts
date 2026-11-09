import type { ActivityEntry } from "@/features/activity/types";
import type { Incident } from "@/features/incidents/types";

/** Mensajes del backend por /ws/events. */
export type ServerEvent =
  | { type: "sync" }
  | { type: "incident"; incident: Incident }
  | { type: "camera"; cameraId: string; status: string }
  | { type: "analysis"; cameraName: string; entry: ActivityEntry };

export type ToSharedWorker =
  | { type: "join"; establishmentId: string }
  | { type: "leave" };

export type FromSharedWorker =
  | ServerEvent
  | { type: "connection"; connected: boolean; tabs: number };
