"use client";

import { formatTime } from "@/features/incidents/labels";
import { lastFrameUrl } from "./api";
import styles from "./activity.module.css";
import { entryTitle, entryTone, OUTCOME_LABELS, percent, severityLabel } from "./labels";
import type { CameraActivity } from "./types";

/** Movimiento que llena la barra: con 10 % de cambio entre fotogramas ya es mucho. */
const FULL_MOTION = 0.1;

export function CameraActivityCard({ camera }: { camera: CameraActivity }) {
  const last = camera.recent[0];
  const lastAnalysis = camera.recent.find((entry) => entry.assessment);
  const motion = last ? Math.min(last.motion / FULL_MOTION, 1) : 0;
  const streak = lastAnalysis?.streak ?? 0;
  const target = lastAnalysis?.streak_target ?? 2;

  return (
    <article className={styles.tarjeta} aria-labelledby={`camara-${camera.camera_id}`}>
      <div className={styles.cuadro}>
        {camera.has_frame && camera.last_frame_at ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={lastFrameUrl(camera.camera_id, camera.last_frame_at)}
            alt={`Último fotograma que analizó Gemini en ${camera.camera_name}`}
          />
        ) : (
          <p>Aún no hay un fotograma analizado. Gemini mira solo cuando hay movimiento.</p>
        )}
        {last && (
          <span className={styles.estado} data-tono={entryTone(last)}>
            {OUTCOME_LABELS[last.outcome]} · {formatTime(last.at)}
          </span>
        )}
      </div>

      <div className={styles.cuerpo}>
        <h3 id={`camara-${camera.camera_id}`}>{camera.camera_name}</h3>

        <div className={styles.medidor}>
          <span>Movimiento</span>
          <meter min={0} max={1} value={motion} aria-label={`Movimiento ${percent(motion)}`} />
          <span>{last ? percent(last.motion) : "—"}</span>
        </div>

        {lastAnalysis?.assessment ? (
          <div className={styles.respuesta} data-tono={entryTone(lastAnalysis)}>
            <p className={styles.situacion}>{entryTitle(lastAnalysis)}</p>
            <p className={styles.detalle}>
              Confianza {percent(lastAnalysis.assessment.confidence)} · severidad{" "}
              {severityLabel(lastAnalysis.assessment.severity)} · {formatTime(lastAnalysis.at)}
            </p>
            {lastAnalysis.assessment.description && <p>{lastAnalysis.assessment.description}</p>}
          </div>
        ) : (
          <p className={styles.detalle}>Gemini todavía no ha respondido sobre esta cámara.</p>
        )}

        <div className={styles.racha} aria-label={`Confirmación ${streak} de ${target}`}>
          <span>Confirmación</span>
          {Array.from({ length: target }, (_, index) => (
            <span key={index} className={styles.punto} data-lleno={index < streak} />
          ))}
          <span className={styles.detalle}>Se alerta tras {target} detecciones seguidas</span>
        </div>

        <dl className={styles.cifras}>
          <div>
            <dt>Análisis</dt>
            <dd>{camera.counts.analyzed}</dd>
          </div>
          <div>
            <dt>Sin movimiento</dt>
            <dd>{camera.counts.no_motion}</dd>
          </div>
          <div>
            <dt>Fallos</dt>
            <dd>{camera.counts.error}</dd>
          </div>
        </dl>
      </div>
    </article>
  );
}
