"use client";

import { useEffect, useId, useState } from "react";
import styles from "./control.module.css";
import { Icon } from "./icons";

const COLOMBIA = "America/Bogota";

/** Hora de Colombia, actualizada cada segundo, como texto y como marca de tiempo. */
export function useClock(): { text: string; now: number } {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return {
    text: now.toLocaleTimeString("es-CO", { hour12: false, timeZone: COLOMBIA }),
    now: now.getTime(),
  };
}

/** Mini-gráfica de una serie real. Sin datos, una línea plana. */
export function Sparkline({ values, color }: { values: number[]; color: string }) {
  const id = useId().replace(/:/g, "");
  const width = 78;
  const height = 28;
  const points = values.length > 1 ? values : [0, 0];
  const max = Math.max(...points, 1);
  const step = width / (points.length - 1);
  const path = points
    .map((value, index) => {
      const x = (index * step).toFixed(1);
      const y = (height - 2 - (value / max) * (height - 4)).toFixed(1);
      return `${index ? "L" : "M"}${x} ${y}`;
    })
    .join(" ");

  return (
    <svg className={styles.sparkline} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.35" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L${width} ${height} L0 ${height} Z`} fill={`url(#${id})`} />
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}

interface StatCardProps {
  label: string;
  icon: string;
  value: string;
  note: string;
  tone: "ok" | "critico" | "info";
  series: number[];
  color: string;
}

export function StatCard({ label, icon, value, note, tone, series, color }: StatCardProps) {
  return (
    <article className={`${styles.vidrio} ${styles.tarjeta}`}>
      <div className={styles.tarjetaCabecera}>
        <h2 style={{ font: "inherit" }}>{label}</h2>
        <Icon name={icon} />
      </div>
      <p className={styles.valor}>{value}</p>
      <p className={styles.sub} data-tono={tone}>
        {note}
      </p>
      <Sparkline values={series} color={color} />
    </article>
  );
}
