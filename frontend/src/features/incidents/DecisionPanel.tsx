"use client";

import { DecisionActions } from "./DecisionActions";
import { EvidenceImage } from "./EvidenceImage";
import { formatTime, situationLabel, statusLabel } from "./labels";
import type { Incident } from "./types";
import styles from "./DecisionPanel.module.css";

interface DecisionPanelProps {
  incident: Incident | null;
  caiNumber: string | null;
  onChange: (incident: Incident) => void;
}

export function DecisionPanel({ incident, caiNumber, onChange }: DecisionPanelProps) {
  if (!incident) {
    return (
      <aside className={styles.panel} aria-label="Decisión">
        <h2 className={styles.calma}>Todo en calma</h2>
        <p className={styles.tenue}>Cuando una cámara detecte algo, lo verás aquí para decidir.</p>
        <EmergencyCall />
      </aside>
    );
  }

  return (
    <aside className={styles.panel} aria-label="Decisión" aria-live="assertive">
      <div className={styles.encabezado} data-estado={incident.status}>
        <h2>{situationLabel(incident.type)}</h2>
        <p>
          {incident.camera_name} a las {formatTime(incident.detected_at)}
        </p>
      </div>

      <EvidenceImage
        className={styles.evidencia}
        incidentId={incident.id}
        alt={`Fotograma de ${incident.camera_name}: ${incident.description}`}
      />
      <p>{incident.description}</p>
      <p className={styles.estado}>{statusLabel(incident.type, incident.status)}</p>

      <DecisionActions
        key={incident.id}
        incident={incident}
        caiNumber={caiNumber}
        onChange={onChange}
      />
      <EmergencyCall />
    </aside>
  );
}

function EmergencyCall() {
  return (
    <a className={styles.linea} href="tel:123">
      Llama al 123
    </a>
  );
}
