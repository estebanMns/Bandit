import { situationLabel } from "@/features/incidents/labels";
import type { ActivityEntry, ActivityOutcome, SyncRun } from "./types";

export const OUTCOME_LABELS: Record<ActivityOutcome, string> = {
  analyzed: "Analizado por Gemini",
  no_motion: "Sin movimiento",
  over_budget: "Tope diario alcanzado",
  error: "Falló la consulta",
  filtered: "Respuesta descartada por privacidad",
};

const SEVERITY: Record<string, string> = {
  low: "baja",
  medium: "media",
  high: "alta",
};

const TRIGGERS: Record<SyncRun["trigger"], string> = {
  startup: "al arrancar",
  scheduled: "programada",
  manual: "manual",
};

/** Lo que se lee en la línea de tiempo: la situación si hubo análisis, si no el motivo. */
export function entryTitle(entry: ActivityEntry): string {
  if (entry.outcome !== "analyzed" || !entry.assessment) return OUTCOME_LABELS[entry.outcome];
  if (entry.assessment.type === "none") return "Escena tranquila";
  return situationLabel(entry.assessment.type);
}

/** Tono visual: alerta, en observación, normal o apagado. */
export function entryTone(entry: ActivityEntry): "alerta" | "observacion" | "calma" | "apagado" {
  if (entry.alerted) return "alerta";
  if (entry.outcome === "error" || entry.outcome === "over_budget") return "observacion";
  if (entry.assessment && entry.assessment.type !== "none") return "observacion";
  if (entry.outcome === "analyzed") return "calma";
  return "apagado";
}

export function severityLabel(severity: string): string {
  return SEVERITY[severity] ?? severity;
}

export function triggerLabel(trigger: SyncRun["trigger"]): string {
  return TRIGGERS[trigger];
}

export function percent(value: number): string {
  return `${Math.round(value * 100)} %`;
}
