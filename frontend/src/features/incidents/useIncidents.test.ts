import { describe, expect, it, vi } from "vitest";
import type { AuditEntry, Incident, IncidentStatus } from "./types";

vi.mock("@/features/live/useLiveEvents", () => ({ useLiveEvents: vi.fn() }));
vi.mock("./api", () => ({ listIncidents: vi.fn() }));

const { upsertIncident } = await import("./useIncidents");

function incident(id: string, status: IncidentStatus, steps: number, detectedAt: string): Incident {
  const audit: AuditEntry[] = Array.from({ length: steps }, () => ({
    status,
    at: detectedAt,
    actor: "sistema",
  }));
  return {
    id,
    establishment_id: "local",
    camera_id: "camara",
    camera_name: "Barra",
    type: "fight",
    severity: "high",
    confidence: 0.9,
    description: "",
    detected_at: detectedAt,
    status,
    audit,
  };
}

describe("upsertIncident", () => {
  const time = "2026-11-05T02:00:00Z";

  it("aplica una versión más nueva", () => {
    const result = upsertIncident(
      [incident("a", "detected", 1, time)],
      incident("a", "confirmed", 2, time),
    );

    expect(result[0]?.status).toBe("confirmed");
  });

  it("ignora una respuesta atrasada que llega después del evento", () => {
    const result = upsertIncident(
      [incident("a", "notified", 3, time)],
      incident("a", "confirmed", 2, time),
    );

    expect(result[0]?.status).toBe("notified");
  });

  it("ordena del más reciente al más antiguo", () => {
    const result = upsertIncident(
      [incident("viejo", "detected", 1, "2026-11-05T01:00:00Z")],
      incident("nuevo", "detected", 1, "2026-11-05T02:00:00Z"),
    );

    expect(result.map((item) => item.id)).toEqual(["nuevo", "viejo"]);
  });
});
