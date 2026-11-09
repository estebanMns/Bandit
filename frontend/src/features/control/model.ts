/** Lógica pura del centro de control: eventos, severidad, series por hora y estado del sistema. */
import type { ActivitySnapshot } from "@/features/activity/types";
import { situationLabel } from "@/features/incidents/labels";
import type { Incident } from "@/features/incidents/types";

export type Severity = "CRITICO" | "ALTO" | "MEDIO" | "BAJO";

export interface ControlEvent {
  id: string;
  at: string;
  title: string;
  place: string;
  severity: Severity;
  thumbnail: string | null;
  href: string;
}

function incidentSeverity(incident: Incident): Severity {
  if (incident.status === "detected") return incident.severity === "high" ? "CRITICO" : "ALTO";
  if (incident.status === "notification_failed") return "ALTO";
  return "BAJO";
}

const INCIDENT_TITLES: Partial<Record<Incident["status"], string>> = {
  notified: "Aviso enviado al CAI",
  discarded: "Falsa alarma descartada",
  confirmed: "Confirmada, avisando al CAI",
  notification_failed: "Falló el aviso al CAI",
};

/** Incidentes y evaluaciones con situación de la IA, del más reciente al más antiguo. */
export function controlEvents(
  incidents: Incident[],
  snapshot: ActivitySnapshot | null,
  limit = 12,
): ControlEvent[] {
  const fromIncidents = incidents.map<ControlEvent>((incident) => ({
    id: `i-${incident.id}`,
    at: incident.detected_at,
    title:
      incident.status === "detected"
        ? situationLabel(incident.type)
        : (INCIDENT_TITLES[incident.status] ?? situationLabel(incident.type)),
    place: incident.camera_name,
    severity: incidentSeverity(incident),
    thumbnail: `/api/incidents/${incident.id}/evidence`,
    href: `/incidentes/${incident.id}`,
  }));
  const fromAnalysis = (snapshot?.cameras ?? []).flatMap((camera) =>
    camera.recent
      .filter((entry) => entry.assessment && entry.assessment.type !== "none" && !entry.alerted)
      .map<ControlEvent>((entry) => ({
        id: `a-${camera.camera_id}-${entry.at}`,
        at: entry.at,
        title: `${situationLabel(entry.assessment!.type)} en observación`,
        place: camera.camera_name,
        severity: "MEDIO",
        thumbnail: null,
        href: "/actividad",
      })),
  );
  return [...fromIncidents, ...fromAnalysis]
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, limit);
}

/** Cuántos elementos caen en cada una de las últimas `hours` horas, de la más antigua a la actual. */
export function hourlySeries(timestamps: string[], now: number, hours = 12): number[] {
  const series = new Array<number>(hours).fill(0);
  for (const timestamp of timestamps) {
    const age = Math.floor((now - Date.parse(timestamp)) / 3_600_000);
    if (age >= 0 && age < hours) series[hours - 1 - age]! += 1;
  }
  return series;
}

export function isToday(timestamp: string, now: number): boolean {
  const zone = { timeZone: "America/Bogota" } as const;
  return (
    new Date(timestamp).toLocaleDateString("es-CO", zone) ===
    new Date(now).toLocaleDateString("es-CO", zone)
  );
}

export interface SystemSignals {
  server: boolean | null;
  realtime: boolean;
  modelEnabled: boolean | null;
  model: string | null;
  caiLinked: boolean;
  imouCloud: boolean | null;
}

export interface StatusRow {
  label: string;
  value: string;
  ok: boolean;
}

export function systemStatus(signals: SystemSignals): StatusRow[] {
  return [
    {
      label: "Servidor",
      value: signals.server ? "Operativo" : "Sin respuesta",
      ok: Boolean(signals.server),
    },
    {
      label: "Tiempo real",
      value: signals.realtime ? "Conectado" : "Reconectando",
      ok: signals.realtime,
    },
    {
      label: "Motor IA",
      value: signals.modelEnabled ? (signals.model ?? "Activo") : "Sin configurar",
      ok: Boolean(signals.modelEnabled),
    },
    {
      label: "Enlace CAI",
      value: signals.caiLinked ? "Enlazado" : "Sin WhatsApp",
      ok: signals.caiLinked,
    },
    {
      label: "Nube Imou",
      value: signals.imouCloud ? "Configurada" : "Sin configurar",
      ok: Boolean(signals.imouCloud),
    },
  ];
}

/** El estado de la cabecera: todo en orden, o lo primero que necesita atención. */
export function overallStatus(rows: StatusRow[]): { ok: boolean; text: string } {
  const essential = rows.filter((row) => row.label !== "Nube Imou");
  const problem = essential.find((row) => !row.ok);
  return problem
    ? { ok: false, text: `Atención: ${problem.label.toLowerCase()} ${problem.value.toLowerCase()}` }
    : { ok: true, text: "Todos los sistemas activos" };
}
