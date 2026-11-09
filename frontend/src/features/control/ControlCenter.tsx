"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LogoutButton } from "@/components/LogoutButton";
import { listWanted } from "@/features/activity/api";
import { useActivity } from "@/features/activity/useActivity";
import { connectionOptions, listCameras, type Camera } from "@/features/cameras/api";
import { AutoConnectCard } from "@/features/cameras/AutoConnectCard";
import { formatReward, priorityRecords } from "@/features/directory/priority";
import type { WantedRecord } from "@/features/directory/types";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { formatTime } from "@/features/incidents/labels";
import { useIncidents } from "@/features/incidents/useIncidents";
import { steps } from "@/features/onboarding/setup";
import { CameraView } from "@/features/video/CameraView";
import { api } from "@/lib/api";
import { CaiMap } from "./CaiMap";
import styles from "./control.module.css";
import { Icon } from "./icons";
import { controlEvents, hourlySeries, isToday, overallStatus, systemStatus } from "./model";
import { StatCard, useClock } from "./widgets";

const NAV = [
  { href: "/panel", label: "Resumen", icon: "resumen" },
  { href: "/monitor", label: "Monitor", icon: "monitor" },
  { href: "/ajustes/camaras", label: "Cámaras", icon: "camaras" },
  { href: "/incidentes", label: "Eventos", icon: "eventos" },
  { href: "/actividad", label: "Analítica", icon: "analitica" },
  { href: "/directorio", label: "Boletín", icon: "boletin" },
  { href: "/ajustes/local", label: "Ajustes", icon: "ajustes" },
];

const ROLES: Record<string, string> = {
  admin: "Administrador",
  owner: "Dueño",
  operator: "Operador",
};
const THEME_KEY = "bandit.tema-control";
const SLOTS = 4;

interface Me {
  email: string;
  role: string;
}

function readTheme(): "centinela" | "centinela-claro" {
  try {
    return localStorage.getItem(THEME_KEY) === "centinela-claro" ? "centinela-claro" : "centinela";
  } catch {
    return "centinela";
  }
}

/** Centro de control: lo primero que se ve al ingresar. Todo con datos reales de Bandit. */
export function ControlCenter() {
  const pathname = usePathname();
  const { text: clock, now } = useClock();
  const { establishments, current, loading, select, reload } = useEstablishment();
  const [theme, setTheme] = useState<"centinela" | "centinela-claro">("centinela");
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [metrics, setMetrics] = useState<Record<string, { live: boolean; fps: number }>>({});
  const [wanted, setWanted] = useState<WantedRecord[]>([]);
  const [me, setMe] = useState<Me | null>(null);
  const [server, setServer] = useState<boolean | null>(null);
  const [imouCloud, setImouCloud] = useState<boolean | null>(null);
  const [eventsOpen, setEventsOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const { incidents, connection } = useIncidents(current?.id);
  const { snapshot } = useActivity(current?.id);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(readTheme());
    api<Me>("/api/auth/me")
      .then(setMe)
      .catch(() => setMe(null));
    fetch("/api/health")
      .then((response) => setServer(response.ok))
      .catch(() => setServer(false));
    connectionOptions()
      .then((options) => setImouCloud(options.imou_cloud))
      .catch(() => setImouCloud(false));
    listWanted()
      .then((records) => setWanted(priorityRecords(records).slice(0, 4)))
      .catch(() => setWanted([]));
  }, []);

  const loadCameras = useCallback(async () => {
    if (current) setCameras(await listCameras(current.id));
  }, [current]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCameras();
  }, [loadCameras]);

  const report = useCallback((id: string, value: { live: boolean; fps: number }) => {
    setMetrics((all) =>
      all[id]?.live === value.live && all[id]?.fps === value.fps ? all : { ...all, [id]: value },
    );
  }, []);

  function changeTheme(next: "centinela" | "centinela-claro") {
    setTheme(next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // Sin almacenamiento el tema solo dura esta visita.
    }
  }

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
  const rows = systemStatus({
    server,
    realtime: connection.connected,
    modelEnabled: snapshot?.model_enabled ?? null,
    model: snapshot?.model ?? null,
    caiLinked: Boolean(current?.cai_whatsapp),
    imouCloud,
  });
  const overall = overallStatus(rows);
  const pendingSteps = steps({
    hasLocal: Boolean(current),
    hasCai: Boolean(current?.cai_whatsapp),
    cameraCount: cameras?.length ?? 0,
  }).filter((step) => !step.done && step.id !== "listo");
  const initials = (me?.email ?? "?").slice(0, 2).toUpperCase();

  return (
    <div className={styles.raiz} data-tema={theme}>
      <div className={styles.layout}>
        <aside className={`${styles.vidrio} ${styles.lateral}`} aria-label="Navegación">
          <Link href="/panel" className={styles.logo}>
            <span className={styles.logoIcono}>
              <Icon name="ojo" size={18} />
            </span>
            <span>
              <b>BANDIT</b>
              <small>CENTRO DE CONTROL</small>
            </span>
          </Link>
          <nav className={styles.nav} aria-label="Principal">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={pathname === item.href ? "page" : undefined}
              >
                <Icon name={item.icon} />
                {item.label}
              </Link>
            ))}
          </nav>
          <div className={styles.espacio} />
          <section
            className={`${styles.vidrio} ${styles.sistema}`}
            aria-labelledby="titulo-sistema"
          >
            <h2 id="titulo-sistema" className={styles.sistemaTitulo}>
              <span className={styles.punto} data-ok={overall.ok} />
              Estado del sistema
            </h2>
            {rows.map((row) => (
              <div key={row.label} className={styles.sistemaFila}>
                <span className={styles.tenue}>{row.label}</span>
                <b data-ok={row.ok}>● {row.value}</b>
              </div>
            ))}
          </section>
          <div className={`${styles.vidrio} ${styles.operador}`}>
            <span className={styles.avatar} aria-hidden="true">
              {initials}
            </span>
            <span className={styles.operadorDatos}>
              <strong>{me?.email ?? "…"}</strong>
              <span>{me ? (ROLES[me.role] ?? me.role) : ""}</span>
            </span>
            <LogoutButton />
          </div>
        </aside>

        <header className={`${styles.vidrio} ${styles.cabecera}`}>
          <div>
            <h1>
              Resumen global
              <span className={styles.estadoGeneral} data-ok={overall.ok}>
                · {overall.text}
              </span>
            </h1>
          </div>
          <div className={styles.herramientas}>
            <button
              type="button"
              className={`${styles.boton} ${styles.botonEventos}`}
              aria-expanded={eventsOpen}
              onClick={() => setEventsOpen((open) => !open)}
            >
              Eventos ({events.length})
            </button>
            <div className={styles.tema} role="group" aria-label="Tema">
              <button
                type="button"
                aria-pressed={theme === "centinela-claro"}
                aria-label="Tema claro"
                onClick={() => changeTheme("centinela-claro")}
              >
                ☀
              </button>
              <button
                type="button"
                aria-pressed={theme === "centinela"}
                aria-label="Tema oscuro"
                onClick={() => changeTheme("centinela")}
              >
                ☾
              </button>
            </div>
            {establishments.length > 1 && (
              <select
                className={styles.selector}
                aria-label="Local"
                value={current?.id ?? ""}
                onChange={(event) => select(event.target.value)}
              >
                {establishments.map((establishment) => (
                  <option key={establishment.id} value={establishment.id}>
                    {establishment.name}
                  </option>
                ))}
              </select>
            )}
            {establishments.length === 1 && current && (
              <span className={styles.selector}>{current.name}</span>
            )}
            <time className={styles.reloj} aria-label="Hora de Colombia">
              {clock}
              <small>COT</small>
            </time>
          </div>
        </header>

        <main className={styles.centro}>
          {!loading && pendingSteps.length > 0 && (
            <div className={`${styles.vidrio} ${styles.aviso}`}>
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
              <section className={`${styles.vidrio} ${styles.panel}`}>
                <h2 className={styles.panelCabecera}>Mapa · Pasto y CAI cercanos</h2>
                <p className={styles.tenue}>Crea tu local para verlo en el mapa.</p>
              </section>
            )}
            <section
              className={`${styles.vidrio} ${styles.panel}`}
              aria-labelledby="titulo-telemetria"
            >
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
          <section
            className={`${styles.vidrio} ${styles.eventos}`}
            aria-labelledby="titulo-eventos"
          >
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

          <section className={`${styles.vidrio} ${styles.panel}`} aria-labelledby="titulo-boletin">
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
    </div>
  );
}
