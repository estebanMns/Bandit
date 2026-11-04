import { describe, expect, it } from "vitest";
import { chooseDecision } from "./decision";
import type { Incident, IncidentStatus } from "./types";

function incident(id: string, status: IncidentStatus): Incident {
  return {
    id,
    establishment_id: "local",
    camera_id: "camara",
    camera_name: "Barra",
    type: "fight",
    severity: "high",
    confidence: 0.9,
    description: "",
    detected_at: "2026-11-05T02:00:00Z",
    status,
    audit: [],
  };
}

describe("chooseDecision", () => {
  it("queda en calma sin incidentes pendientes", () => {
    expect(chooseDecision([incident("a", "discarded")], null)).toBeNull();
  });

  it("nunca oculta un aviso fallido", () => {
    expect(chooseDecision([incident("a", "notification_failed")], null)?.id).toBe("a");
  });

  it("muestra el aviso mientras se envía", () => {
    expect(chooseDecision([incident("a", "confirmed")], null)?.id).toBe("a");
  });

  it("una detección nueva tiene prioridad sobre un aviso fallido", () => {
    const incidents = [incident("fallido", "notification_failed"), incident("nuevo", "detected")];

    expect(chooseDecision(incidents, null)?.id).toBe("nuevo");
  });

  it("respeta la selección del operador si aún requiere atención", () => {
    const incidents = [incident("nuevo", "detected"), incident("fallido", "notification_failed")];

    expect(chooseDecision(incidents, "fallido")?.id).toBe("fallido");
  });

  it("deja ver un incidente resuelto solo si nada más es urgente", () => {
    expect(chooseDecision([incident("a", "notified")], "a")?.id).toBe("a");

    const incidents = [incident("a", "notified"), incident("b", "detected")];
    expect(chooseDecision(incidents, "a")?.id).toBe("b");
  });
});
