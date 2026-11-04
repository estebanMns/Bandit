import { describe, expect, it } from "vitest";
import { positionInShift, shiftWindow } from "./shift";

const at = (iso: string) => Date.parse(iso);

describe("shiftWindow", () => {
  it("usa el turno de noche a las 22:00 de Colombia", () => {
    const window = shiftWindow(at("2026-11-04T22:00:00-05:00"));

    expect(window.start).toBe(at("2026-11-04T18:00:00-05:00"));
    expect(window.end).toBe(at("2026-11-05T06:00:00-05:00"));
    expect(window.ticks.map((tick) => tick.label)).toEqual([
      "18:00",
      "21:00",
      "00:00",
      "03:00",
      "06:00",
    ]);
  });

  it("mantiene el turno de noche después de medianoche", () => {
    const window = shiftWindow(at("2026-11-05T03:00:00-05:00"));

    expect(window.start).toBe(at("2026-11-04T18:00:00-05:00"));
  });

  it("cambia al turno de día exactamente a las 06:00", () => {
    const window = shiftWindow(at("2026-11-05T06:00:00-05:00"));

    expect(window.start).toBe(at("2026-11-05T06:00:00-05:00"));
    expect(window.ticks[0]?.label).toBe("06:00");
    expect(window.ticks[4]?.label).toBe("18:00");
  });
});

describe("positionInShift", () => {
  const window = shiftWindow(at("2026-11-04T22:00:00-05:00"));

  it("ubica la medianoche en el centro del turno", () => {
    expect(positionInShift(at("2026-11-05T00:00:00-05:00"), window)).toBe(0.5);
  });

  it("deja fuera lo que pasó antes del turno", () => {
    expect(positionInShift(at("2026-11-04T17:59:00-05:00"), window)).toBeNull();
  });
});
