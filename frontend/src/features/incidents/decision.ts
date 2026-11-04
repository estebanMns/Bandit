import type { Incident, IncidentStatus } from "./types";

/** De mayor a menor urgencia: un aviso fallido nunca debe quedar oculto. */
const ATTENTION_ORDER: IncidentStatus[] = ["detected", "notification_failed", "confirmed"];

function needsAttention(incident: Incident): boolean {
  return ATTENTION_ORDER.includes(incident.status);
}

/** Elige qué incidente muestra el panel de decisión. */
export function chooseDecision(incidents: Incident[], selectedId: string | null): Incident | null {
  const selected = incidents.find((incident) => incident.id === selectedId) ?? null;
  if (selected && needsAttention(selected)) return selected;

  for (const status of ATTENTION_ORDER) {
    const urgent = incidents.find((incident) => incident.status === status);
    if (urgent) return urgent;
  }
  return selected;
}
