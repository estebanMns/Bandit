import type { WantedRecord } from "./types";

/** El Top 10 del boletín: las recompensas más altas publicadas por la Policía. */
export const PRIORITY_SIZE = 10;

const PESOS = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

export function formatReward(record: Pick<WantedRecord, "reward_amount">): string {
  return record.reward_amount ? PESOS.format(record.reward_amount) : "Sin recompensa publicada";
}

/**
 * El servidor ya entrega el orden: recompensa más alta, luego delito más grave publicado,
 * luego el orden de la página de la Policía. Aquí solo se toma el comienzo.
 */
export function priorityRecords(records: WantedRecord[]): WantedRecord[] {
  return records.slice(0, PRIORITY_SIZE);
}
