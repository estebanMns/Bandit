import { describe, expect, it } from "vitest";
import { formatReward, priorityRecords, PRIORITY_SIZE } from "./priority";
import type { WantedRecord } from "./types";

function record(slug: string): WantedRecord {
  return {
    slug,
    name: slug,
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
  };
}

describe("prioridad del directorio", () => {
  it("muestra la recompensa en pesos colombianos", () => {
    expect(formatReward({ reward_amount: 10_000_000 })).toMatch(/10\.000\.000/);
    expect(formatReward({ reward_amount: null })).toBe("Sin recompensa publicada");
  });

  it("respeta el orden del servidor y toma solo el comienzo", () => {
    const records = Array.from({ length: 9 }, (_, index) => record(`r${index}`));

    expect(priorityRecords(records).map((item) => item.slug)).toEqual(
      records.slice(0, PRIORITY_SIZE).map((item) => item.slug),
    );
  });
});
