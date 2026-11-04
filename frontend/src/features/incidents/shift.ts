/**
 * Ventanas del turno en hora de Colombia (UTC-5, sin horario de verano):
 * noche de 18:00 a 06:00 y día de 06:00 a 18:00.
 */

const HOUR_MS = 3_600_000;
const COLOMBIA_OFFSET_MS = -5 * HOUR_MS;
const SHIFT_HOURS = 12;
const SHIFT_MS = SHIFT_HOURS * HOUR_MS;
/** En hora local, los turnos empiezan a las 06:00 y a las 18:00. */
const FIRST_SHIFT_START_MS = 6 * HOUR_MS;

export interface ShiftWindow {
  start: number;
  end: number;
  ticks: { at: number; label: string }[];
}

function pad(hour: number): string {
  return `${String(hour).padStart(2, "0")}:00`;
}

export function shiftWindow(now: number): ShiftWindow {
  const localNow = now + COLOMBIA_OFFSET_MS;
  const shiftsSinceEpoch = Math.floor((localNow - FIRST_SHIFT_START_MS) / SHIFT_MS);
  const localStart = shiftsSinceEpoch * SHIFT_MS + FIRST_SHIFT_START_MS;
  const start = localStart - COLOMBIA_OFFSET_MS;
  const startHour = Math.round((localStart % (24 * HOUR_MS)) / HOUR_MS);

  const ticks = [0, 3, 6, 9, 12].map((offset) => ({
    at: offset / SHIFT_HOURS,
    label: pad((startHour + offset) % 24),
  }));
  return { start, end: start + SHIFT_MS, ticks };
}

/** Posición de 0 a 1 dentro del turno; `null` si el momento queda fuera. */
export function positionInShift(moment: number, window: ShiftWindow): number | null {
  if (moment < window.start || moment > window.end) return null;
  return (moment - window.start) / (window.end - window.start);
}
