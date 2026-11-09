"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { listCameras, type Camera } from "@/features/cameras/api";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { chooseDecision } from "@/features/incidents/decision";
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
      if (!active) return;
      setCameras(loaded.filter((camera) => camera.enabled));
    });
    return () => {
      active = false;
    };
  }, [current]);

  const featured = cameras.find((camera) => camera.id === selectedCameraId) ?? cameras[0];
  const others = cameras.filter((camera) => camera.id !== featured?.id);
  const decision = chooseDecision(incidents, selectedIncidentId);

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
            <p>Bandit puede buscar tu cámara y conectarla por la red o por la nube.</p>
            <Link href="/panel">Conectarla desde el Panel</Link>
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
            onChange={(incident) => {
              apply(incident);
              setSelectedIncidentId(incident.id);
            }}
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
