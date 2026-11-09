"use client";

import { useEffect, useRef } from "react";
import type { StreamState } from "./protocol";
import { useVideoStream } from "./useVideoStream";
import styles from "./CameraView.module.css";

const STATE_LABEL: Record<StreamState, string> = {
  conectando: "Conectando",
  "en-vivo": "En vivo",
  "sin-senal": "Sin señal, reintentando",
};

interface CameraViewProps {
  cameraId: string;
  name: string;
  featured?: boolean;
  onSelect?: () => void;
  /** Sin el pie propio: quien lo usa pone sus etiquetas encima, como el centro de control. */
  bare?: boolean;
  /** Avisa el estado y los fotogramas por segundo, para la telemetría. */
  onMetrics?: (metrics: { live: boolean; fps: number }) => void;
}

export function CameraView({
  cameraId,
  name,
  featured = false,
  onSelect,
  bare = false,
  onMetrics,
}: CameraViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { state, fps } = useVideoStream(cameraId, canvasRef);

  useEffect(() => {
    onMetrics?.({ live: state === "en-vivo", fps });
  }, [onMetrics, state, fps]);

  const content = (
    <>
      <canvas
        ref={canvasRef}
        className={styles.lienzo}
        role="img"
        aria-label={`Video de ${name}`}
      />
      {state !== "en-vivo" && <p className={styles.aviso}>{STATE_LABEL[state]}</p>}
      {!bare && (
        <div className={styles.pie}>
          <span className={styles.nombre}>{name}</span>
          <span className={styles.estado} data-estado={state}>
            <span aria-hidden="true" className={styles.marca} />
            {STATE_LABEL[state]}
            {featured && state === "en-vivo" && fps > 0 ? ` a ${fps} fps` : ""}
          </span>
        </div>
      )}
    </>
  );

  if (onSelect) {
    return (
      <button type="button" className={styles.vista} onClick={onSelect}>
        {content}
      </button>
    );
  }
  return <figure className={styles.vista}>{content}</figure>;
}
