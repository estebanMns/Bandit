"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { FaceWatchPanel } from "@/features/faces/FaceWatchPanel";
import styles from "./activity.module.css";
import { ActivityTimeline } from "./ActivityTimeline";
import { CameraActivityCard } from "./CameraActivityCard";
import { DirectoryPanel } from "./DirectoryPanel";
import { timeline } from "./state";
import { useActivity } from "./useActivity";

export function ActivityDashboard() {
  const { current, loading } = useEstablishment();
  const { snapshot, error, connection } = useActivity(current?.id);
  const items = useMemo(() => (snapshot ? timeline(snapshot) : []), [snapshot]);
  const budget = snapshot?.budget;

  return (
    <main className={styles.panel}>
      <header className={styles.cabecera}>
        <div>
          <h1>Actividad de la IA</h1>
          <p className={styles.detalle}>
            Lo que Gemini mira en cada cámara, lo que concluye y cuándo confirma una situación.
            Las situaciones nunca identifican personas; la prueba de rostros solo compara con
            personas de prueba que dieron su consentimiento.
          </p>
        </div>
        <dl className={styles.resumen}>
          <div>
            <dt>Modelo</dt>
            <dd data-activo={snapshot?.model_enabled ?? false}>
              {snapshot ? (snapshot.model_enabled ? "Gemini activo" : "Sin GEMINI_API_KEY") : "—"}
            </dd>
          </div>
          <div>
            <dt>Consultas hoy</dt>
            <dd>
              {budget ? `${budget.used} de ${budget.limit}` : "—"}
              {budget && (
                <meter min={0} max={budget.limit} value={budget.used} aria-hidden="true" />
              )}
            </dd>
          </div>
          <div>
            <dt>En vivo</dt>
            <dd data-activo={connection.connected}>
              {connection.connected ? "Conectado" : "Reconectando"}
            </dd>
          </div>
        </dl>
      </header>

      {!loading && !current && (
        <p>
          Crea primero tu local en <Link href="/ajustes/local">Local</Link>.
        </p>
      )}
      {error && (
        <p role="alert">No se pudo leer la actividad. Revisa que el servidor esté encendido.</p>
      )}

      {current && !snapshot && !error && (
        <p className={styles.detalle} role="status">
          Cargando la actividad…
        </p>
      )}

      {snapshot && (
        <div className={styles.rejilla}>
          <section className={`vidrio ${styles.seccion}`} aria-labelledby="titulo-camaras">
            <h2 id="titulo-camaras">Cámaras</h2>
            {snapshot.cameras.length === 0 ? (
              <p className={styles.detalle}>
                Ninguna cámara ha enviado video todavía.{" "}
                <Link href="/ajustes/camaras" className={styles.enlace}>
                  Agrega una cámara
                </Link>
                : en cuanto esté en vivo y haya movimiento, Gemini empieza a analizarla.
              </p>
            ) : (
              <div className={styles.tarjetas}>
                {snapshot.cameras.map((camera) => (
                  <CameraActivityCard key={camera.camera_id} camera={camera} />
                ))}
              </div>
            )}
          </section>

          <section className={`vidrio ${styles.seccion}`} aria-labelledby="titulo-linea">
            <h2 id="titulo-linea">Últimos análisis</h2>
            <ActivityTimeline items={items} />
          </section>
        </div>
      )}

      {current && <FaceWatchPanel establishmentId={current.id} />}

      <DirectoryPanel />
    </main>
  );
}
