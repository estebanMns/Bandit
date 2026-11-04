"use client";

import { useEffect, useMemo, useState } from "react";
import { formatTime, situationLabel, STATUS_LABELS } from "./labels";
import { positionInShift, shiftWindow } from "./shift";
import type { Incident } from "./types";
import styles from "./ShiftLine.module.css";

interface ShiftLineProps {
  incidents: Incident[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  /** Permite fijar el reloj en la demostración de la portada. */
  nowOverride?: number;
}

const REFRESH_MS = 30_000;

function percent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function ShiftLine({ incidents, selectedId, onSelect, nowOverride }: ShiftLineProps) {
  const [clock, setClock] = useState(() => Date.now());
  const now = nowOverride ?? clock;

  useEffect(() => {
    if (nowOverride !== undefined) return;
    const timer = setInterval(() => setClock(Date.now()), REFRESH_MS);
    return () => clearInterval(timer);
  }, [nowOverride]);

  const window = useMemo(() => shiftWindow(now), [now]);
  const progress = positionInShift(now, window) ?? 0;
  const marks = incidents.flatMap((incident) => {
    const position = positionInShift(Date.parse(incident.detected_at), window);
    return position === null ? [] : [{ incident, position }];
  });

  return (
    <section className={styles.turno} aria-label="Línea del turno">
      <div className={styles.pista}>
        <div className={styles.transcurrido} style={{ width: percent(progress) }} />
        <div className={styles.ahora} style={{ left: percent(progress) }} aria-hidden="true" />
        {marks.map(({ incident, position }) => (
          <button
            key={incident.id}
            type="button"
            className={styles.marca}
            data-estado={incident.status}
            data-seleccionada={incident.id === selectedId || undefined}
            style={{ left: percent(position) }}
            onClick={() => onSelect?.(incident.id)}
            aria-label={`${situationLabel(incident.type)}, ${formatTime(incident.detected_at)}, ${STATUS_LABELS[incident.status]}`}
          />
        ))}
      </div>
      <ol className={styles.horas} aria-hidden="true">
        {window.ticks.map((tick) => (
          <li key={tick.at} style={{ left: percent(tick.at) }}>
            {tick.label}
          </li>
        ))}
      </ol>
    </section>
  );
}
