import { describe, expect, it } from "vitest";
import { firstPending, needsSetup, steps } from "./setup";

describe("primeros pasos", () => {
  it("una cuenta nueva sin local empieza por el local", () => {
    const state = { hasLocal: false, hasCai: false, cameraCount: 0 };

    expect(firstPending(state)).toBe("local");
    expect(needsSetup(state)).toBe(true);
  });

  it("con local pide el WhatsApp del CAI y luego las cámaras", () => {
    expect(firstPending({ hasLocal: true, hasCai: false, cameraCount: 0 })).toBe("cai");
    expect(firstPending({ hasLocal: true, hasCai: true, cameraCount: 0 })).toBe("camaras");
  });

  it("el CAI es opcional para empezar a vigilar", () => {
    const state = { hasLocal: true, hasCai: false, cameraCount: 2 };

    expect(needsSetup(state)).toBe(false);
    expect(steps(state).find((step) => step.id === "listo")?.done).toBe(true);
  });

  it("con todo listo termina en el último paso", () => {
    expect(firstPending({ hasLocal: true, hasCai: true, cameraCount: 1 })).toBe("listo");
  });
});
