/**
 * URL de un WebSocket del backend.
 *
 * Se pide un ticket de un minuto a /api/auth/ws-ticket (con la cookie de sesión, por el mismo
 * dominio) y el backend responde también adónde conectarse (`ws_url`). Así funciona igual detrás
 * de Caddy que con el frontend en Vercel y el backend en Render, sin variables que haya que
 * acertar al compilar: Vercel no reenvía WebSockets, el navegador va directo al backend.
 * NEXT_PUBLIC_BACKEND_WS_URL, si existe, manda sobre lo que diga el backend.
 * Sirve también dentro de workers.
 */
const OVERRIDE = (process.env.NEXT_PUBLIC_BACKEND_WS_URL ?? "").replace(/\/$/, "");

interface TicketResponse {
  ticket: string;
  ws_url?: string;
}

function sameOrigin(path: string): string {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.host}${path}`;
}

export async function backendSocketUrl(path: string): Promise<string> {
  let response: Response;
  try {
    response = await fetch("/api/auth/ws-ticket", {
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    return sameOrigin(path);
  }
  if (!response.ok) {
    // Sin sesión no hay ticket: con un backend en otro dominio no hay cómo conectarse.
    if (OVERRIDE) throw new Error(`No se pudo obtener el ticket (${response.status})`);
    return sameOrigin(path);
  }
  const { ticket, ws_url: backend } = (await response.json()) as TicketResponse;
  const base = (OVERRIDE || backend || "").replace(/\/$/, "");
  if (!base) return sameOrigin(path);
  return `${base}${path}?ticket=${encodeURIComponent(ticket)}`;
}
