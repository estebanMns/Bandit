import { describe, expect, it } from "vitest";
import { filterDirectory, uniqueValues } from "./filter";
import type { WantedRecord } from "./types";

function record(name: string, changes: Partial<WantedRecord> = {}): WantedRecord {
  return {
    slug: name,
    name,
    alias: null,
    crime: null,
    reward: null,
    region: null,
    hotline_email: null,
    hotline_phones: [],
    photo_url: null,
    flyer_url: null,
    source_url: "",
    last_seen_at: null,
    reward_amount: null,
    crime_level: null,
    ...changes,
  };
}

const records = [
  record("Andrés Ejemplo", { alias: "El Primero", crime: "Hurto", region: "Nariño" }),
  record("Beatriz Prueba", { crime: "Extorsión", region: "Cauca" }),
];
const none = { search: "", crime: "", region: "" };

describe("filterDirectory", () => {
  it("sin filtros muestra todos", () => {
    expect(filterDirectory(records, none)).toHaveLength(2);
  });

  it("busca por nombre sin importar tildes ni mayúsculas", () => {
    expect(filterDirectory(records, { ...none, search: "ANDRES" })).toEqual([records[0]]);
  });

  it("busca por alias", () => {
    expect(filterDirectory(records, { ...none, search: "primero" })).toEqual([records[0]]);
  });

  it("combina delito y región", () => {
    expect(filterDirectory(records, { ...none, crime: "Hurto", region: "Cauca" })).toEqual([]);
  });
});

describe("uniqueValues", () => {
  it("quita vacíos y repetidos, y ordena en español", () => {
    expect(uniqueValues(["Ñame", null, "Zeta", "Ñame", "Ana"])).toEqual(["Ana", "Ñame", "Zeta"]);
  });
});
