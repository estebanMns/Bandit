"use client";

import { useEffect, useRef, useState } from "react";
import type { FromSharedWorker, ServerEvent, ToSharedWorker } from "./protocol";

interface LiveConnection {
  connected: boolean;
  tabs: number;
}

/** Recibe eventos por el SharedWorker o, si el navegador no lo tiene, por un WebSocket propio. */
export function useLiveEvents(
  establishmentId: string | undefined,
  onEvent: (event: ServerEvent) => void,
): LiveConnection {
  const [connection, setConnection] = useState<LiveConnection>({ connected: false, tabs: 0 });
  const handler = useRef(onEvent);

  useEffect(() => {
    handler.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!establishmentId) return;

    if (typeof SharedWorker === "undefined") {
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${protocol}//${location.host}/ws/events/${establishmentId}`);
      socket.onopen = () => setConnection({ connected: true, tabs: 1 });
      socket.onclose = () => setConnection({ connected: false, tabs: 1 });
      socket.onmessage = (event: MessageEvent<string>) =>
        handler.current(JSON.parse(event.data) as ServerEvent);
      return () => socket.close();
    }

    const worker = new SharedWorker(new URL("./events.shared-worker.ts", import.meta.url), {
      type: "module",
      name: "bandit-eventos",
    });
    const { port } = worker;
    port.onmessage = (event: MessageEvent<FromSharedWorker>) => {
      const message = event.data;
      if (message.type === "connection") {
        setConnection({ connected: message.connected, tabs: message.tabs });
      } else {
        handler.current(message);
      }
    };
    port.start();
    port.postMessage({ type: "join", establishmentId } satisfies ToSharedWorker);

    const leave = () => port.postMessage({ type: "leave" } satisfies ToSharedWorker);
    window.addEventListener("pagehide", leave);
    return () => {
      window.removeEventListener("pagehide", leave);
      leave();
      port.close();
    };
  }, [establishmentId]);

  return connection;
}
