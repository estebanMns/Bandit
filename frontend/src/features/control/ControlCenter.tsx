"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ControlShell } from "@/components/ControlShell";
import { listWanted } from "@/features/activity/api";
import { useActivity } from "@/features/activity/useActivity";
import { listCameras, type Camera } from "@/features/cameras/api";
import { AutoConnectCard } from "@/features/cameras/AutoConnectCard";
import { formatReward, priorityRecords } from "@/features/directory/priority";
import type { WantedRecord } from "@/features/directory/types";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { formatTime } from "@/features/incidents/labels";
import { useIncidents } from "@/features/incidents/useIncidents";
import { steps } from "@/features/onboarding/setup";
import { CameraView } from "@/features/video/CameraView";
import { CaiMap } from "./CaiMap";
import styles from "./control.module.css";
import { Icon } from "./icons";
import { controlEvents, hourlySeries, isToday } from "./model";
import { StatCard, useClock } from "./widgets";

const SLOTS = 4;

/** Centro de control: lo primero que se ve al ingresar. Todo con datos reales de Bandit. */
const CAMERA_REFRESH_MS = 20_000;

export function ControlCenter() {
  const { text: clock, now } = useClock();
  const { current, loading, reload } = useEstablishment();
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [metrics, setMetrics] = useState<Record<string, { live: boolean; fps: number }>>({});
  const [wanted, setWanted] = useState<WantedRecord[]>([]);
  const [eventsOpen, setEventsOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const { incidents } = useIncidents(current?.id);
  const { snapshot } = useActivity(current?.id);

  useEffect(() => {
    listWanted()
      .then((records) => setWanted(priorityRecords(records).slice(0, 4)))
      .catch(() => setWanted([]));
  }, []);

  const loadCameras = useCallback(async () => {
    if (!current) return;
    try {
      setCameras(await listCameras(current.id));
    } catch {
      // Se conserva la última lista conocida; el próximo intento la actualiza.
    }
  }, [current]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCameras();
    // El estado y el motivo de cada cámara cambian en el servidor: se revisan cada 20 s.
    const timer = setInterval(() => void loadCameras(), CAMERA_REFRESH_MS);
    return () => clearInterval(timer);
  }, [loadCameras]);

  const report = useCallback((id: string, value: { live: boolean; fps: number }) => {
    setMetrics((all) =>
      all[id]?.live === value.live && all[id]?.fps === value.fps ? all : { ...all, [id]: value },
    );
  }, []);

  const enabled = (cameras ?? []).filter((camera) => camera.enabled);
  const liveCount = enabled.filter(
    (camera) => metrics[camera.id]?.live ?? camera.status === "live",
  ).length;
  const today = incidents.filter((incident) => isToday(incident.detected_at, now));
  const pending = incidents.filter((incident) => incident.status === "detected");
  const critical = pending.filter((incident) => incident.severity === "high");
  const analyses = (snapshot?.cameras ?? []).flatMap((camera) =>
    camera.recent.filter((entry) => entry.outcome === "analyzed").map((entry) => entry.at),
  );
  const motion = (snapshot?.cameras[0]?.recent ?? [])
    .slice(0, 20)
    .reverse()
    .map((entry) => Math.round(entry.motion * 100));
  const events = useMemo(() => controlEvents(incidents, snapshot), [incidents, snapshot]);
  const pendingSteps = steps({
    hasLocal: Boolean(current),
    hasCai: Boolean(current?.cai_whatsapp),
    cameraCount: cameras?.length ?? 0,
  }).filter((step) => !step.done && step.id !== "listo");

  return (
    <ControlShell
      title="Resumen global"
      heading
      actions={
        <button
          type="button"
          className={`${styles.boton} ${styles.botonEventos}`}
          aria-expanded={eventsOpen}
          onClick={() => setEventsOpen((open) => !open)}
        >
          Eventos ({events.length})
        </button>
      }
    >
      <div className={styles.grid}>
        <main className={styles.centro}>
          {!loading && pendingSteps.length > 0 && (
            <div className={`vidrio ${styles.aviso}`}>
              <span>
                <strong>Te falta configurar:</strong>{" "}
                {pendingSteps.map((step) => step.title).join(" · ")}
              </span>
              <Link href="/empezar">Completar</Link>
            </div>
          )}

          <div className={styles.tarjetas}>
            <StatCard
              label="Situaciones hoy"
              icon="eventos"
              value={String(today.length)}
              note={today.length ? `${pending.length} por revisar` : "Sin situaciones"}
              tone={today.length ? "info" : "ok"}
              series={hourlySeries(
                incidents.map((incident) => incident.detected_at),
                now,
              )}
              color="#56b4ff"
            />
            <StatCard
              label="Cámaras en vivo"
              icon="camaras"
              value={`${liveCount}/${enabled.length}`}
              note={liveCount ? "● En línea" : "Sin video"}
              tone={liveCount ? "ok" : "critico"}
              series={motion}
              color="#35d6a4"
            />
            <StatCard
              label="Alertas por revisar"
              icon="eventos"
              value={String(pending.length)}
              note={critical.length ? `▲ ${critical.length} críticas` : "Nada urgente"}
              tone={critical.length ? "critico" : "ok"}
              series={hourlySeries(
                pending.map((incident) => incident.detected_at),
                now,
              )}
              color="#ff4d4f"
            />
            <StatCard
              label="Análisis IA hoy"
              icon="analitica"
              value={String(snapshot?.budget.used ?? 0)}
              note={
                snapshot?.model_enabled
                  ? `de ${snapshot.budget.limit} · ${snapshot.model ?? "IA"}`
                  : "IA sin configurar"
              }
              tone={snapshot?.model_enabled ? "info" : "critico"}
              series={hourlySeries(analyses, now)}
              color="#56b4ff"
            />
          </div>

          <section className={styles.camaras} aria-label="Cámaras">
            {Array.from({ length: SLOTS }, (_, index) => {
              const camera = enabled[index];
              if (!camera) {
                return (
                  <button
                    key={`vacia-${index}`}
                    type="button"
                    className={`${styles.camara} ${styles.vacia}`}
                    onClick={() => dialog.current?.showModal()}
                    disabled={!current}
                  >
                    <Icon name="mas" size={22} />
                    <strong>Conectar cámara</strong>
                    <span>CAM-0{index + 1} · casilla libre</span>
                  </button>
                );
              }
              const live = metrics[camera.id]?.live ?? camera.status === "live";
              return (
                <div key={camera.id} className={styles.camara}>
                  <CameraView
                    cameraId={camera.id}
                    name={camera.name}
                    problem={camera.problem}
                    bare
                    onMetrics={(value) => report(camera.id, value)}
                  />
                  <span className={styles.etiqueta}>
                    <span className={styles.punto} data-ok={live} aria-hidden="true" />
                    CAM-0{index + 1} · {camera.name}
                  </span>
                  <span className={styles.hora} aria-hidden="true">
                    {clock}
                  </span>
                </div>
              );
            })}
          </section>

          <div className={styles.abajo}>
            {current ? (
              <CaiMap establishment={current} onLocated={reload} />
            ) : (
              <section className={`vidrio ${styles.panel}`}>
                <h2 className={styles.panelCabecera}>Mapa · Pasto y CAI cercanos</h2>
                <p className={styles.tenue}>Crea tu local para verlo en el mapa.</p>
              </section>
            )}
            <section className={`vidrio ${styles.panel}`} aria-labelledby="titulo-telemetria">
              <div className={styles.panelCabecera}>
                <h2 id="titulo-telemetria">Telemetría de cámaras</h2>
                <Link href="/actividad" className={styles.enlace}>
                  Analítica
                </Link>
              </div>
              {enabled.length === 0 ? (
                <p className={styles.tenue}>Sin cámaras conectadas todavía.</p>
              ) : (
                <ul className={styles.telemetria}>
                  {enabled.map((camera, index) => {
                    const activity = snapshot?.cameras.find((c) => c.camera_id === camera.id);
                    const last = activity?.recent[0];
                    const live = metrics[camera.id]?.live ?? camera.status === "live";
                    return (
                      <li key={camera.id} className={styles.unidad}>
                        <span>
                          <strong>CAM-0{index + 1}</strong>
                          <small>{camera.name}</small>
                        </span>
                        <span className={styles.medida}>
                          {metrics[camera.id]?.fps ?? 0}
                          <small>FPS</small>
                        </span>
                        <span className={styles.medida}>
                          {last ? `${Math.round(last.motion * 100)}%` : "—"}
                          <small>MOV.</small>
                        </span>
                        <span className={styles.medida}>
                          {activity?.counts.analyzed ?? 0}
                          <small>IA HOY</small>
                        </span>
                        <span className={styles.vivo} data-vivo={live}>
                          <span className={styles.punto} data-ok={live} aria-hidden="true" />
                          {live ? "Live" : "Sin video"}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          </div>
        </main>

        <aside className={styles.derecha} data-abierta={eventsOpen} aria-label="Eventos y boletín">
          <section className={`vidrio ${styles.eventos}`} aria-labelledby="titulo-eventos">
            <div className={styles.eventosCabecera}>
              <h2 id="titulo-eventos">Eventos en vivo</h2>
              <span className={`${styles.tenue} ${styles.cifra}`}>{pending.length} activos</span>
            </div>
            {events.length === 0 ? (
              <p className={styles.tenue} style={{ padding: 16 }}>
                Sin eventos todavía. Aquí aparece cada alerta y lo que la IA observa.
              </p>
            ) : (
              <ol className={styles.lista}>
                {events.map((event, index) => (
                  <li key={event.id} className={styles.evento} data-severidad={event.severity}>
                    <Link href={event.href}>
                      <span className={styles.linea} aria-hidden="true">
                        <i />
                        {index < events.length - 1 && <span />}
                      </span>
                      <span>
                        <span className={styles.eventoHora}>{formatTime(event.at)}</span>
                        <span className={styles.eventoTitulo} style={{ display: "block" }}>
                          {event.title}
                        </span>
                        <span className={styles.eventoLugar}>{event.place}</span>
                        <br />
                        <span className={styles.severidad}>
                          {event.severity === "CRITICO" ? "CRÍTICO" : event.severity}
                        </span>
                      </span>
                      <span className={styles.miniatura}>
                        {event.thumbnail && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={event.thumbnail}
                            alt=""
                            loading="lazy"
                            onError={(error) => {
                              error.currentTarget.style.display = "none";
                            }}
                          />
                        )}
                      </span>
                    </Link>
                  </li>
                ))}
              </ol>
            )}
            <Link href="/incidentes" className={styles.verTodos}>
              Ver todos los eventos
            </Link>
          </section>

          <section className={`vidrio ${styles.panel}`} aria-labelledby="titulo-boletin">
            <div className={styles.panelCabecera}>
              <h2 id="titulo-boletin">Más buscados · prioridad</h2>
              <Link href="/directorio" className={styles.enlace}>
                Boletín
              </Link>
            </div>
            {wanted.length === 0 ? (
              <p className={styles.tenue}>El boletín todavía no tiene registros.</p>
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
        </aside>
      </div>

      <dialog ref={dialog} className={styles.dialogo} aria-labelledby="titulo-conectar">
        <div className={styles.dialogoCabecera}>
          <h2 id="titulo-conectar">Conectar cámara</h2>
          <button
            type="button"
            className={styles.boton}
            onClick={() => dialog.current?.close()}
            aria-label="Cerrar"
          >
            <Icon name="cerrar" />
          </button>
        </div>
        {current && (
          <AutoConnectCard
            establishmentId={current.id}
            onConnected={() => {
              dialog.current?.close();
              void loadCameras();
            }}
          />
        )}
      </dialog>
    </ControlShell>
  );
}
