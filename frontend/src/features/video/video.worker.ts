/// <reference lib="webworker" />

import { FrameRing, MAX_FRAME_HEIGHT, MAX_FRAME_WIDTH } from "./frameRing";
import type { FromWorker, ToWorker } from "./protocol";
import { backendSocketUrl } from "../live/socket-url";

/** Decodifica JPEG fuera del hilo principal para que la interfaz nunca se trabe. */

const MAX_RETRY_MS = 30_000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const METRICS_INTERVAL_MS = 1_000;

const scope = self as unknown as DedicatedWorkerGlobalScope;

let socket: WebSocket | null = null;
// Cada start/stop invalida las conexiones que aún esperaban su ticket.
let generation = 0;
let ring: FrameRing | null = null;
let retryTimer: ReturnType<typeof setTimeout> | undefined;
let retryDelay = 1_000;
let stopped = false;
let decoding = false;
let framesThisSecond = 0;
const canvas = new OffscreenCanvas(1, 1);
const context = canvas.getContext("2d", { willReadFrequently: true });

function send(message: FromWorker, transfer: Transferable[] = []): void {
  scope.postMessage(message, transfer);
}

async function decode(jpeg: ArrayBuffer): Promise<void> {
  // Si la decodificación se atrasa, se salta el fotograma: importa el más reciente.
  if (decoding) return;
  decoding = true;
  try {
    const bitmap = await createImageBitmap(new Blob([jpeg], { type: "image/jpeg" }));
    framesThisSecond += 1;
    if (!ring || !context) {
      send({ type: "frame", bitmap }, [bitmap]);
      return;
    }
    const scale = Math.min(1, MAX_FRAME_WIDTH / bitmap.width, MAX_FRAME_HEIGHT / bitmap.height);
    const width = Math.floor(bitmap.width * scale);
    const height = Math.floor(bitmap.height * scale);
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    context.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();
    ring.write(context.getImageData(0, 0, width, height).data, width, height);
  } finally {
    decoding = false;
  }
}

function scheduleRetry(cameraId: string): void {
  send({ type: "state", state: "sin-senal" });
  retryTimer = setTimeout(() => void connect(cameraId), retryDelay);
  retryDelay = Math.min(retryDelay * 2, MAX_RETRY_MS);
}

async function connect(cameraId: string): Promise<void> {
  send({ type: "state", state: "conectando" });
  const attempt = generation;
  if (!UUID.test(cameraId)) {
    send({ type: "state", state: "sin-senal" });
    return;
  }
  let url: string;
  try {
    url = await backendSocketUrl(`/ws/video/${encodeURIComponent(cameraId)}`);
  } catch {
    if (!stopped && attempt === generation) scheduleRetry(cameraId);
    return;
  }
  if (stopped || attempt !== generation) return;
  const connection = new WebSocket(url);
  connection.binaryType = "arraybuffer";
  socket = connection;

  connection.onmessage = (event: MessageEvent<ArrayBuffer>) => {
    retryDelay = 1_000;
    send({ type: "state", state: "en-vivo" });
    void decode(event.data);
  };
  connection.onclose = () => {
    if (stopped) return;
    scheduleRetry(cameraId);
  };
}

setInterval(() => {
  send({ type: "metrics", fps: framesThisSecond });
  framesThisSecond = 0;
}, METRICS_INTERVAL_MS);

scope.onmessage = (event: MessageEvent<ToWorker>) => {
  const message = event.data;
  generation += 1;
  if (message.type === "start") {
    stopped = false;
    ring = message.ring ? new FrameRing(message.ring) : null;
    void connect(message.cameraId);
    return;
  }
  stopped = true;
  clearTimeout(retryTimer);
  socket?.close();
};
