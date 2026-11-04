"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { listCameras, type Camera } from "@/features/cameras/api";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { DecisionPanel } from "@/features/incidents/DecisionPanel";
import { ShiftLine } from "@/features/incidents/ShiftLine";
import { useIncidents } from "@/features/incidents/useIncidents";
import { CameraView } from "@/features/video/CameraView";
import styles from "./monitor.module.css";

export function MonitorClient() {
  const { current, loading } = useEstablishment();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const { incidents, connection, apply } = useIncidents(current?.id);

  useEffect(() => {
    if (!current) return;
    let active = true;
    listCameras(current.id).then((loaded) => {
      if (active) setCameras(loaded.filter((camera) => camera.enabled));
    });
    return () => {
      active = false;
    };
  }, [current]);

  const featured = cameras.find((camera) => camera.id === selectedCameraId) ?? cameras[0];
  const others = cameras.filter((camera) => camera.id !== featured?.id);
  const pending = incidents.find((incident) => incident.status === "detected");
  const decision =
    incidents.find((incident) => incident.id === selectedIncidentId) ?? pending ?? null;

  return (
    <AppShell
      aside={
        <span className={styles.conexion} data-conectado={connection.connected}>
          {connection.connected ? "Alertas activas" : "Reconectando alertas"}
        </span>
      }
    >
      <main className={styles.monitor}>
        {!loading && !featured && (
          <div className={styles.vacio}>
            <h1>Conecta tu primera cámara</h1>
            <p>Agrega la dirección RTSP y aquí verás el video en vivo.</p>
            <Link href="/ajustes/camaras">Agregar cámara</Link>
          </div>
        )}
        {featured && (
          <section className={styles.principal} aria-label="Cámara seleccionada">
            <CameraView key={featured.id} cameraId={featured.id} name={featured.name} featured />
          </section>
        )}
        {others.length > 0 && (
          <section className={styles.tira} aria-label="Otras cámaras">
            {others.map((camera) => (
              <CameraView
                key={camera.id}
                cameraId={camera.id}
                name={camera.name}
                onSelect={() => setSelectedCameraId(camera.id)}
              />
            ))}
          </section>
        )}
        {featured && (
          <DecisionPanel
            incident={decision}
            caiNumber={current?.cai_whatsapp ?? null}
            onChange={apply}
          />
        )}
        {featured && (
          <ShiftLine
            incidents={incidents}
            selectedId={decision?.id}
            onSelect={setSelectedIncidentId}
          />
        )}
      </main>
    </AppShell>
  );
}
