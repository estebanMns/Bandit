import { describe, expect, it } from "vitest";
import { decisionTexts, statusLabel } from "./labels";

describe("textos de decisión", () => {
  it("una persona buscada se acepta o se rechaza con sus propias palabras", () => {
    const texts = decisionTexts("wanted_match");

    expect(texts.confirm).toContain("es la persona buscada");
    expect(texts.discard).toBe("No es la persona buscada");
    expect(texts.check).toContain("foto del registro");
  });

  it("las demás situaciones conservan confirmar y descartar", () => {
    expect(decisionTexts("weapon").confirm).toBe("Confirmar y avisar al CAI");
    expect(decisionTexts("weapon").discard).toBe("Descartar");
  });

  it("el rechazo de una persona buscada se lee como tal", () => {
    expect(statusLabel("wanted_match", "discarded")).toBe("Rechazado: no era la persona");
    expect(statusLabel("weapon", "discarded")).toBe("Descartado");
    expect(statusLabel("wanted_match", "detected")).toBe("Por revisar");
  });
});
