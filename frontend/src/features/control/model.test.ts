import { describe, expect, it } from "vitest";
import type { ActivitySnapshot } from "@/features/activity/types";
import type { Incident } from "@/features/incidents/types";
import { controlEvents, hourlySeries, overallStatus, systemStatus } from "./model";

const NOW = Date.parse("2026-11-09T20:00:00Z");

function incident(id: string, at: string, status: Incident["status"], severity = "high"): Incident {
  return {
    id,
    establishment_id: "l",
    camera_id: "c",
    camera_name: "Barra",
    type: "fight",
    severity,
    confidence: 0.9,
    description: "",
    detected_at: at,
    status,
    audit: [],
  };
}

const SNAPSHOT: ActivitySnapshot = {
  model_enabled: true,
  budget: { used: 3, limit: 10 },
  cameras: [
    {
      camera_id: "c",
      camera_name: "Barra",
      counts: { analyzed: 2, no_motion: 0, over_budget: 0, error: 0, filtered: 0 },
      has_frame: true,
      last_frame_at: null,
      recent: [
        {
          camera_id: "c",
          at: "2026-11-09T19:59:00Z",
          outcome: "analyzed",
          motion: 0.1,
          assessment: { type: "weapon", severity: "high", confidence: 0.8, description: "" },
          streak: 1,
          streak_target: 2,
          alerted: false,
        },
        {
          camera_id: "c",
          at: "2026-11-09T19:58:00Z",
          outcome: "analyzed",
          motion: 0.1,
          assessment: { type: "none", severity: "low", confidence: 1, description: "" },
          streak: 0,
          streak_target: 2,
          alerted: false,
        },
      ],
    },
  ],
};

describe("eventos del centro de control", () => {
  it("mezcla incidentes y observaciones de la IA, del más reciente al más antiguo", () => {
    const events = controlEvents(
      [
        incident("a", "2026-11-09T19:00:00Z", "notified"),
        incident("b", "2026-11-09T19:30:00Z", "detected"),
      ],
      SNAPSHOT,
    );

    expect(events.map((event) => [event.title, event.severity])).toEqual([
      ["Arma visible en observación", "MEDIO"],
      ["Pelea", "CRITICO"],
      ["Aviso enviado al CAI", "BAJO"],
    ]);
  });

  it("una alerta por revisar de severidad media es ALTO, no CRÍTICO", () => {
    const [event] = controlEvents(
      [incident("a", "2026-11-09T19:00:00Z", "detected", "medium")],
      null,
    );

    expect(event!.severity).toBe("ALTO");
  });
});

describe("series por hora", () => {
  it("cuenta en la hora correcta y descarta lo viejo", () => {
    const series = hourlySeries(
      [
        "2026-11-09T19:30:00Z",
        "2026-11-09T19:45:00Z",
        "2026-11-09T17:10:00Z",
        "2026-11-08T10:00:00Z",
      ],
      NOW,
      4,
    );

    expect(series).toEqual([0, 1, 0, 2]);
  });
});

describe("estado del sistema", () => {
  const signals = {
    server: true,
    realtime: true,
    modelEnabled: true,
    model: "gemini-3.5-flash",
    caiLinked: true,
    imouCloud: false,
  };

  it("la nube de Imou es opcional para estar en orden", () => {
    expect(overallStatus(systemStatus(signals))).toEqual({
      ok: true,
      text: "Todos los sistemas activos",
    });
  });

  it("avisa lo primero que necesita atención", () => {
    const status = overallStatus(systemStatus({ ...signals, caiLinked: false }));

    expect(status.ok).toBe(false);
    expect(status.text).toContain("enlace cai");
  });
});
