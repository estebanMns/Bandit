import { describe, expect, it } from "vitest";
import { applyEntry, RECENT_LIMIT, timeline } from "./state";
import type { ActivityEntry, ActivitySnapshot } from "./types";

const EMPTY: ActivitySnapshot = {
  model_enabled: true,
  budget: { used: 0, limit: 10 },
  cameras: [],
};

function entry(
  second: number,
  outcome: ActivityEntry["outcome"] = "analyzed",
  camera = "c1",
): ActivityEntry {
  return {
    camera_id: camera,
    at: `2026-11-08T22:00:${String(second).padStart(2, "0")}Z`,
    outcome,
    motion: 0.1,
    assessment: null,
    streak: 0,
    streak_target: 2,
    alerted: false,
  };
}

describe("applyEntry", () => {
  it("crea la cámara la primera vez que llega su actividad", () => {
    const next = applyEntry(EMPTY, "Barra", entry(1));

    expect(next.cameras).toHaveLength(1);
    expect(next.cameras[0]!.camera_name).toBe("Barra");
    expect(next.cameras[0]!.counts.analyzed).toBe(1);
    expect(next.cameras[0]!.has_frame).toBe(true);
  });

  it("solo descuenta del presupuesto lo que consultó al modelo", () => {
    let state = applyEntry(EMPTY, "Barra", entry(1, "no_motion"));
    state = applyEntry(state, "Barra", entry(2, "over_budget"));
    state = applyEntry(state, "Barra", entry(3, "analyzed"));
    state = applyEntry(state, "Barra", entry(4, "error"));

    expect(state.budget.used).toBe(2);
  });

  it("una escena quieta no cambia el último fotograma", () => {
    let state = applyEntry(EMPTY, "Barra", entry(1));
    state = applyEntry(state, "Barra", entry(2, "no_motion"));

    expect(state.cameras[0]!.last_frame_at).toBe(entry(1).at);
  });

  it("ignora mensajes repetidos o atrasados", () => {
    const state = applyEntry(EMPTY, "Barra", entry(5));

    expect(applyEntry(state, "Barra", entry(5))).toBe(state);
    expect(applyEntry(state, "Barra", entry(3))).toBe(state);
  });

  it("guarda solo lo reciente", () => {
    let state = EMPTY;
    for (let second = 0; second < RECENT_LIMIT + 5; second += 1) {
      state = applyEntry(state, "Barra", {
        ...entry(0),
        at: new Date(Date.UTC(2026, 10, 8, 22, 0, second)).toISOString(),
      });
    }

    expect(state.cameras[0]!.recent).toHaveLength(RECENT_LIMIT);
  });
});

describe("timeline", () => {
  it("mezcla las cámaras de la más reciente a la más antigua", () => {
    let state = applyEntry(EMPTY, "Barra", entry(1, "analyzed", "c1"));
    state = applyEntry(state, "Puerta", entry(3, "analyzed", "c2"));
    state = applyEntry(state, "Barra", entry(2, "analyzed", "c1"));

    expect(timeline(state).map((item) => `${item.camera_name}:${item.at.slice(-3)}`)).toEqual([
      "Puerta:03Z",
      "Barra:02Z",
      "Barra:01Z",
    ]);
  });
});
