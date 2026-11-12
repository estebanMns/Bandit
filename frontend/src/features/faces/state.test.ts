import { describe, expect, it } from "vitest";
import { applyCheck, comparedFaces } from "./state";
import type { FaceCheck, FaceWatch } from "./types";

const watch: FaceWatch = {
  enabled: true,
  model: "modelo",
  people: ["Persona Prueba"],
  used: 1,
  limit: 300,
  counts: { match: 0, no_match: 1, no_face: 0, error: 0 },
  recent: [],
};

const check: FaceCheck = {
  id: "c1",
  camera_id: "cam",
  camera_name: "Entrada",
  at: "2026-11-12T20:00:00Z",
  outcome: "match",
  person: "Persona Prueba",
  confidence: 0.95,
  explanation: "Mismos rasgos.",
  alerted: true,
};

describe("applyCheck", () => {
  it("cuenta la comparación nueva y la pone primero", () => {
    const next = applyCheck(watch, check);

    expect(next.counts.match).toBe(1);
    expect(next.used).toBe(2);
    expect(next.recent[0]).toBe(check);
    expect(comparedFaces(next)).toBe(2);
  });

  it("no repite una comparación que ya estaba", () => {
    const once = applyCheck(watch, check);

    expect(applyCheck(once, check)).toBe(once);
  });
});
