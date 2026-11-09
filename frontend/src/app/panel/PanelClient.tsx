"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { listWanted } from "@/features/activity/api";
import { entryTitle } from "@/features/activity/labels";
import { useActivity } from "@/features/activity/useActivity";
import { listCameras, type Camera } from "@/features/cameras/api";
import { AutoConnectCard } from "@/features/cameras/AutoConnectCard";
import { formatReward, priorityRecords } from "@/features/directory/priority";
import type { WantedRecord } from "@/features/directory/types";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { formatTime, situationLabel, STATUS_LABELS } from "@/features/incidents/labels";
import { useIncidents } from "@/features/incidents/useIncidents";
import { steps } from "@/features/onboarding/setup";
import { CameraView } from "@/features/video/CameraView";
import styles from "./panel.module.css";

const STATUS_TEXT: Record<Camera["status"], string> = {
  live: "En vivo",
  connecting: "Conectando",
  retrying: "Reintentando",
  stopped: "Detenida",
};

/** Inicio después de ingresar: todo lo importante en una sola pantalla, sin redirecciones. */
export function PanelClient() {
  const { current, loading } = useEstablishment();
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [wanted, setWanted] = useState<WantedRecord[]>([]);
  const [connecting, setConnecting] = useState(false);
  const { incidents } = useIncidents(current?.id);
  const { snapshot } = useActivity(current?.id);

  const loadCameras = useCallback(async () => {
    if (current) setCameras(await listCameras(current.id));
  }, [current]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCameras();
  }, [loadCameras]);

  useEffect(() => {
    listWanted()
      .then((records) => setWanted(priorityRecords(records).slice(0, 4)))
      .catch(() => setWanted([]));
  }, []);

  const setup = steps({
    hasLocal: Boolean(current),
    hasCai: Boolean(current?.cai_whatsapp),
    cameraCount: cameras?.length ?? 0,
  });
  const pendingSteps = setup.filter((step) => !step.done && step.id !== "listo");
  const pendingAlerts = incidents.filter((incident) => incident.status === "detected");
  const lastAnalysis = snapshot?.cameras
    .flatMap((camera) => camera.recent.map((entry) => ({ ...entry, camera: camera.camera_name })))
    .filter((entry) => entry.assessment)
    .sort((a, b) => b.at.localeCompare(a.at))[0];
  const enabled = (cameras ?? []).filter((camera) => camera.enabled);
  const showConnect = connecting || (cameras !== null && cameras.length === 0);

  return (
    <AppShell>
      <main className={styles.panel}>
        <header className={styles.cabecera}>
          <div>
            <p className={styles.eyebrow}>Panel</p>
            <h1>{current ? current.name : loading ? "Cargando…" : "Bienvenido a Bandit"}</h1>
          </div>
          <ul className={styles.chips} aria-label="Resumen">
            <li data-tono={enabled.length ? "ok" : "alerta"}>
              {enabled.length === 1 ? "1 cámara" : `${enabled.length} cámaras`}
            </li>
            <li data-tono={pendingAlerts.length ? "alerta" : "ok"}>
              {pendingAlerts.length === 1
                ? "1 alerta por revisar"
                : `${pendingAlerts.length} alertas por revisar`}
            </li>
            <li data-tono={snapshot?.model_enabled ? "ok" : "alerta"}>
              {snapshot?.model_enabled ? `IA: ${snapshot.model ?? "activa"}` : "IA sin configurar"}
            </li>
          </ul>
        </header>

        {!loading && pendingSteps.length > 0 && (
          <section className={styles.aviso} aria-labelledby="titulo-configuracion">
            <div>
              <h2 id="titulo-configuracion">Te falta configurar</h2>
              <p>{pendingSteps.map((step) => step.title).join(" · ")}</p>
            </div>
            <Link href="/empezar" className={styles.boton}>
              Completar
            </Link>
          </section>
        )}

        <div className={styles.rejilla}>
          <section
            className={`${styles.tarjeta} ${styles.camaras}`}
            aria-labelledby="titulo-camaras"
          >
            <div className={styles.tarjetaCabecera}>
              <h2 id="titulo-camaras">Cámaras</h2>
              {current && cameras && cameras.length > 0 && (
                <button
                  type="button"
                  className={styles.enlace}
                  onClick={() => setConnecting((v) => !v)}
                >
                  {connecting ? "Cerrar" : "Conectar otra cámara"}
                </button>
              )}
            </div>
            {enabled.length > 0 && (
              <div className={styles.videos}>
                {enabled.map((camera) => (
                  <figure key={camera.id} className={styles.video}>
                    <CameraView cameraId={camera.id} name={camera.name} />
                    <figcaption>
                      <span>{camera.name}</span>
                      <span className={styles.estado} data-estado={camera.status}>
                        {STATUS_TEXT[camera.status]}
                      </span>
                    </figcaption>
                  </figure>
                ))}
              </div>
            )}
            {current && showConnect && (
              <AutoConnectCard
                establishmentId={current.id}
                onConnected={() => {
                  setConnecting(false);
                  void loadCameras();
                }}
              />
            )}
            {!current && !loading && (
              <p>
                Crea tu local para conectar cámaras. <Link href="/empezar">Empezar</Link>
              </p>
            )}
          </section>

          <section className={styles.tarjeta} aria-labelledby="titulo-alertas">
            <div className={styles.tarjetaCabecera}>
              <h2 id="titulo-alertas">Alertas</h2>
              <Link href="/monitor" className={styles.enlace}>
                Abrir Monitor
              </Link>
            </div>
            {incidents.length === 0 ? (
              <p className={styles.tenue}>
                Sin alertas por ahora. Gemini avisa aquí cuando vea algo.
              </p>
            ) : (
              <ul className={styles.lista}>
                {incidents.slice(0, 4).map((incident) => (
                  <li key={incident.id} data-pendiente={incident.status === "detected"}>
                    <strong>{situationLabel(incident.type)}</strong>
                    <span className={styles.tenue}>
                      {incident.camera_name} · {formatTime(incident.detected_at)} ·{" "}
                      {STATUS_LABELS[incident.status]}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={styles.tarjeta} aria-labelledby="titulo-ia">
            <div className={styles.tarjetaCabecera}>
              <h2 id="titulo-ia">Inteligencia artificial</h2>
              <Link href="/actividad" className={styles.enlace}>
                Ver actividad
              </Link>
            </div>
            {snapshot ? (
              <dl className={styles.datos}>
                <div>
                  <dt>Modelo</dt>
                  <dd>
                    {snapshot.model_enabled ? (snapshot.model ?? "Activo") : "Sin GEMINI_API_KEY"}
                  </dd>
                </div>
                <div>
                  <dt>Consultas hoy</dt>
                  <dd>
                    {snapshot.budget.used} de {snapshot.budget.limit}
                  </dd>
                </div>
                <div>
                  <dt>Último análisis</dt>
                  <dd>
                    {lastAnalysis
                      ? `${entryTitle(lastAnalysis)} · ${lastAnalysis.camera} · ${formatTime(lastAnalysis.at)}`
                      : "Aún sin análisis: empieza cuando una cámara esté en vivo y haya movimiento."}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className={styles.tenue}>Cargando…</p>
            )}
          </section>

          <section className={styles.tarjeta} aria-labelledby="titulo-buscados">
            <div className={styles.tarjetaCabecera}>
              <h2 id="titulo-buscados">Más buscados</h2>
              <Link href="/directorio" className={styles.enlace}>
                Ver directorio
              </Link>
            </div>
            {wanted.length === 0 ? (
              <p className={styles.tenue}>El directorio todavía no tiene registros.</p>
            ) : (
              <ul className={styles.buscados}>
                {wanted.map((record) => (
                  <li key={record.slug}>
                    <Link href={`/directorio/${record.slug}`}>
                      {record.photo_url && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={record.photo_url} alt="" />
                      )}
                      <span>
                        <strong>{record.name}</strong>
                        <span className={styles.tenue}>{formatReward(record)}</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </main>
    </AppShell>
  );
}
