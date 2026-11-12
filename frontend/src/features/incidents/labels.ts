import type { IncidentStatus } from "./types";

const SITUATIONS: Record<string, string> = {
  weapon: "Arma visible",
  robbery: "Atraco o hurto",
  fight: "Pelea",
  fire: "Fuego o humo",
  medical: "Emergencia de salud",
  wanted_match: "Persona buscada identificada",
};

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  detected: "Por revisar",
  confirmed: "Avisando al CAI",
  discarded: "Descartado",
  notified: "CAI avisado",
  notification_failed: "Falló el aviso",
};

const COLOMBIA = "America/Bogota";

export function situationLabel(type: string): string {
  return SITUATIONS[type] ?? "Situación detectada";
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: COLOMBIA,
  }).format(new Date(iso));
}

export function formatTime(iso: string): string {
  return new Intl.DateTimeFormat("es-CO", { timeStyle: "short", timeZone: COLOMBIA }).format(
    new Date(iso),
  );
}
