/** Mensajes entre la página y el Web Worker de video. */

export type StreamState = "conectando" | "en-vivo" | "sin-senal";

export type ToWorker =
  | { type: "start"; cameraId: string; ring: SharedArrayBuffer | null }
  | { type: "stop" };

export type FromWorker =
  | { type: "state"; state: StreamState }
  | { type: "metrics"; fps: number }
  /** Solo sin aislamiento cross-origin: el fotograma viaja por transferencia. */
  | { type: "frame"; bitmap: ImageBitmap };
