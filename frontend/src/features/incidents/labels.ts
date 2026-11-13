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

const WANTED_MATCH = "wanted_match";

/** Estado visible de un incidente; un rechazo de persona buscada se dice como tal. */
export function statusLabel(type: string, status: IncidentStatus): string {
  if (type === WANTED_MATCH && status === "discarded") return "Rechazado: no era la persona";
  return STATUS_LABELS[status];
}

export interface DecisionTexts {
  confirm: string;
  discard: string;
  question: string;
  /** Qué debe haber comprobado el operador antes de avisar al CAI. */
  check: string;
}

/** Textos de los botones de decisión según lo que se detectó. */
export function decisionTexts(type: string): DecisionTexts {
  if (type === WANTED_MATCH) {
    return {
      confirm: "Sí, es la persona buscada · avisar al CAI",
      discard: "No es la persona buscada",
      question: "¿Es la persona buscada?",
      check: "Confirma solo si comparaste el video con la foto del registro.",
    };
  }
  return {
    confirm: "Confirmar y avisar al CAI",
    discard: "Descartar",
    question: "¿Avisar al CAI?",
    check: "Confirma solo si viste la situación en el video.",
  };
}

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
