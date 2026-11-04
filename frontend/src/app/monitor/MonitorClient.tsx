"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { listCameras, type Camera } from "@/features/cameras/api";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { CameraView } from "@/features/video/CameraView";
import styles from "./monitor.module.css";

export function MonitorClient() {
  const { current, loading } = useEstablishment();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

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

  const featured = cameras.find((camera) => camera.id === selectedId) ?? cameras[0];
  const others = cameras.filter((camera) => camera.id !== featured?.id);

  return (
    <AppShell>
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
                onSelect={() => setSelectedId(camera.id)}
              />
            ))}
          </section>
        )}
      </main>
    </AppShell>
  );
}
