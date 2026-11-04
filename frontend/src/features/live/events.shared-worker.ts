/// <reference lib="webworker" />

import type { FromSharedWorker, ServerEvent, ToSharedWorker } from "./protocol";

/**
 * Una sola conexión a /ws/events por local, sin importar cuántas pestañas estén
 * abiertas. El worker reparte cada evento a todas las pestañas (fan-out).
 */

interface Channel {
  ports: Set<MessagePort>;
  socket: WebSocket | null;
  connected: boolean;
  retryDelay: number;
  retryTimer?: ReturnType<typeof setTimeout>;
}

const MAX_RETRY_MS = 30_000;
const scope = self as unknown as SharedWorkerGlobalScope;
const channels = new Map<string, Channel>();
const portChannels = new Map<MessagePort, string>();

function broadcast(channel: Channel, message: FromSharedWorker): void {
  channel.ports.forEach((port) => port.postMessage(message));
}

function announce(channel: Channel): void {
  broadcast(channel, {
    type: "connection",
    connected: channel.connected,
    tabs: channel.ports.size,
  });
}

function connect(establishmentId: string, channel: Channel): void {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${location.host}/ws/events/${establishmentId}`);
  channel.socket = socket;

  socket.onopen = () => {
    channel.connected = true;
    channel.retryDelay = 1_000;
    announce(channel);
  };
  socket.onmessage = (event: MessageEvent<string>) => {
    broadcast(channel, JSON.parse(event.data) as ServerEvent);
  };
  socket.onclose = () => {
    channel.connected = false;
    channel.socket = null;
    if (channel.ports.size === 0) return;
    announce(channel);
    channel.retryTimer = setTimeout(() => connect(establishmentId, channel), channel.retryDelay);
    channel.retryDelay = Math.min(channel.retryDelay * 2, MAX_RETRY_MS);
  };
}

function leave(port: MessagePort): void {
  const establishmentId = portChannels.get(port);
  portChannels.delete(port);
  if (!establishmentId) return;
  const channel = channels.get(establishmentId);
  if (!channel) return;
  channel.ports.delete(port);
  if (channel.ports.size > 0) {
    announce(channel);
    return;
  }
  clearTimeout(channel.retryTimer);
  channel.socket?.close();
  channels.delete(establishmentId);
}

function join(port: MessagePort, establishmentId: string): void {
  leave(port);
  let channel = channels.get(establishmentId);
  if (!channel) {
    channel = { ports: new Set(), socket: null, connected: false, retryDelay: 1_000 };
    channels.set(establishmentId, channel);
    channel.ports.add(port);
    connect(establishmentId, channel);
  } else {
    channel.ports.add(port);
  }
  portChannels.set(port, establishmentId);
  // Una pestaña nueva pide resincronizar porque no vio los eventos anteriores.
  port.postMessage({ type: "sync" } satisfies FromSharedWorker);
  announce(channel);
}

scope.onconnect = (event: MessageEvent) => {
  const port = event.ports[0];
  if (!port) return;
  port.onmessage = (message: MessageEvent<ToSharedWorker>) => {
    if (message.data.type === "join") join(port, message.data.establishmentId);
    else leave(port);
  };
  port.start();
};
