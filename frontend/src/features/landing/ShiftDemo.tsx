"use client";

import { ShiftLine } from "@/features/incidents/ShiftLine";
import type { Incident } from "@/features/incidents/types";
import styles from "./landing.module.css";

/** Demostración con datos de ejemplo: ninguna cámara ni persona real. */

const NOW = Date.parse("2026-11-05T01:40:00-05:00");

function sample(id: string, time: string, status: Incident["status"], type: string): Incident {
  return {
    id,
    establishment_id: "demo",
    camera_id: "demo",
    camera_name: "Barra",
    type,
    severity: "high",
    confidence: 0.9,
    description: "",
    detected_at: time,
    status,
    audit: [],
  };
}

const SAMPLES = [
  sample("descartada", "2026-11-04T20:15:00-05:00", "discarded", "fight"),
  sample("avisada", "2026-11-04T22:50:00-05:00", "notified", "robbery"),
  sample("pendiente", "2026-11-05T01:32:00-05:00", "detected", "fight"),
];

export function ShiftDemo() {
  return (
    <figure className={styles.demo}>
      <ShiftLine incidents={SAMPLES} nowOverride={NOW} />
      <figcaption>
        Ejemplo de un turno: una falsa alarma descartada, un aviso enviado al CAI y una pelea por
        revisar.
      </figcaption>
    </figure>
  );
}
