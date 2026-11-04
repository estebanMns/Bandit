"use client";

import { useEffect, useState, type RefObject } from "react";
import { FrameRing, frameRingBytes } from "./frameRing";
import type { FromWorker, StreamState, ToWorker } from "./protocol";

export interface VideoStream {
  state: StreamState;
  fps: number;
  shared: boolean;
}

function paintShared(ring: FrameRing, canvas: HTMLCanvasElement, lastSequence: number): number {
  const info = ring.latest();
  const context = canvas.getContext("2d");
  if (!info || !context || info.sequence === lastSequence) return lastSequence;
  if (canvas.width !== info.width || canvas.height !== info.height) {
    canvas.width = info.width;
    canvas.height = info.height;
  }
  const image = context.createImageData(info.width, info.height);
  ring.copyLatestInto(image.data);
  context.putImageData(image, 0, 0);
  return info.sequence;
}

export function useVideoStream(
  cameraId: string,
  canvasRef: RefObject<HTMLCanvasElement | null>,
): VideoStream {
  const [state, setState] = useState<StreamState>("conectando");
  const [fps, setFps] = useState(0);
  const [shared] = useState(() => typeof window !== "undefined" && window.crossOriginIsolated);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const worker = new Worker(new URL("./video.worker.ts", import.meta.url), { type: "module" });
    const buffer = shared ? new SharedArrayBuffer(frameRingBytes()) : null;
    const ring = buffer ? new FrameRing(buffer) : null;
    let animation = 0;
    let lastSequence = 0;

    worker.onmessage = (event: MessageEvent<FromWorker>) => {
      const message = event.data;
      if (message.type === "state") setState(message.state);
      if (message.type === "metrics") setFps(message.fps);
      if (message.type === "frame") {
        canvas.width = message.bitmap.width;
        canvas.height = message.bitmap.height;
        canvas.getContext("2d")?.drawImage(message.bitmap, 0, 0);
        message.bitmap.close();
      }
    };

    if (ring) {
      const render = () => {
        lastSequence = paintShared(ring, canvas, lastSequence);
        animation = requestAnimationFrame(render);
      };
      animation = requestAnimationFrame(render);
    }

    worker.postMessage({ type: "start", cameraId, ring: buffer } satisfies ToWorker);

    return () => {
      cancelAnimationFrame(animation);
      worker.postMessage({ type: "stop" } satisfies ToWorker);
      worker.terminate();
    };
  }, [cameraId, canvasRef, shared]);

  return { state, fps, shared };
}
