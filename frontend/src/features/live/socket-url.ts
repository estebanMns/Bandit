/**
 * URL de un WebSocket del backend.
 *
 * Detrás de Caddy (o en desarrollo) el WebSocket va al mismo dominio y la cookie de
 * sesión basta. Si el frontend vive en otro dominio (Vercel), NEXT_PUBLIC_BACKEND_WS_URL
 * apunta al backend y se pide antes un ticket de un minuto, porque el navegador no envía
 * la cookie de sesión a otro dominio. Sirve también dentro de workers.
 */
const BACKEND_WS_URL = (process.env.NEXT_PUBLIC_BACKEND_WS_URL ?? "").replace(/\/$/, "");

export async function backendSocketUrl(path: string): Promise<string> {
  if (!BACKEND_WS_URL) {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${location.host}${path}`;
  }
  const response = await fetch("/api/auth/ws-ticket", {
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`No se pudo obtener el ticket (${response.status})`);
  const { ticket } = (await response.json()) as { ticket: string };
  return `${BACKEND_WS_URL}${path}?ticket=${encodeURIComponent(ticket)}`;
}
