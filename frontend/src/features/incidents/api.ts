import { api } from "@/lib/api";
import type { Incident } from "./types";

export function listIncidents(establishmentId: string): Promise<Incident[]> {
  return api(`/api/establishments/${establishmentId}/incidents`);
}

export function confirmIncident(id: string): Promise<Incident> {
  return api(`/api/incidents/${id}/confirm`, { method: "POST" });
}

export function discardIncident(id: string): Promise<Incident> {
  return api(`/api/incidents/${id}/discard`, { method: "POST" });
}
