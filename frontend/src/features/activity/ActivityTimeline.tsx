import { formatTime } from "@/features/incidents/labels";
import styles from "./activity.module.css";
import { entryTitle, entryTone, percent } from "./labels";
import type { ActivityEntry } from "./types";

type Item = ActivityEntry & { camera_name: string };

/** Cada muestreo de todas las cámaras, en orden: lo que miró el modelo y qué concluyó. */
export function ActivityTimeline({ items }: { items: Item[] }) {
  if (items.length === 0) {
    return (
      <p className={styles.detalle}>Cuando una cámara esté en vivo, aquí aparece cada análisis.</p>
    );
  }

  return (
    <ol className={styles.linea} aria-live="polite" aria-relevant="additions">
      {items.map((item) => (
        <li key={`${item.camera_id}-${item.at}`} data-tono={entryTone(item)}>
          <time dateTime={item.at}>{formatTime(item.at)}</time>
          <span className={styles.lineaCamara}>{item.camera_name}</span>
          <span className={styles.lineaTitulo}>
            {entryTitle(item)}
            {item.alerted && " · alerta creada"}
          </span>
          <span className={styles.detalle}>
            {item.assessment
              ? `${percent(item.assessment.confidence)} de confianza`
              : `movimiento ${percent(item.motion)}`}
          </span>
        </li>
      ))}
    </ol>
  );
}
