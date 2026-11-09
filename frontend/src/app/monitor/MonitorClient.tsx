"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { listCameras, type Camera } from "@/features/cameras/api";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { chooseDecision } from "@/features/incidents/decision";
import { DecisionPanel } from "@/features/incidents/DecisionPanel";
import { ShiftLine } from "@/features/incidents/ShiftLine";
import { useIncidents } from "@/features/incidents/useIncidents";
import { LATER_KEY, needsSetup } from "@/features/onboarding/setup";
import { CameraView } from "@/features/video/CameraView";
import styles from "./monitor.module.css";

export function MonitorClient() {
  const router = useRouter();
  const { current, loading } = useEstablishment();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [registered, setRegistered] = useState<number | null>(null);
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const { incidents, connection, apply } = useIncidents(current?.id);

  useEffect(() => {
    if (!current) return;
    let active = true;
    listCameras(current.id).then((loaded) => {
      if (!active) return;
      setRegistered(loaded.length);
      setCameras(loaded.filter((camera) => camera.enabled));
    });
    return () => {
      active = false;
    };
  }, [current]);

  // Una cuenta sin local o sin cámaras va a los primeros pasos, salvo que haya pedido hacerlo luego.
  useEffect(() => {
    if (loading || (current && registered === null)) return;
    const state = { hasLocal: Boolean(current), hasCai: false, cameraCount: registered ?? 0 };
    if (needsSetup(state) && !sessionStorage.getItem(LATER_KEY)) router.replace("/empezar");
  }, [loading, current, registered, router]);

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
            <p>Bandit puede buscar las cámaras de tu Wi-Fi y conectarlas por ti.</p>
            <Link href="/empezar">Terminar la configuración</Link>
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
