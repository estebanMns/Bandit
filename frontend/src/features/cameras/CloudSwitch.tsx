"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { cached } from "@/lib/cache";
import { autoConnect, connectionOptions, setCameraEnabled, type Camera } from "./api";
import styles from "./CloudSwitch.module.css";

const PRIVATE_NETWORK = "private_network";
const OPTIONS_MAX_AGE_MS = 5 * 60_000;

/**
 * Cuando el servidor no alcanza una cámara de una red privada (por ejemplo el backend en la
 * nube y la cámara en el Wi-Fi del local), la conecta por la nube de Imou y desactiva la vieja.
 */
export function CloudSwitch({ camera, onDone }: { camera: Camera; onDone: () => void }) {
  const [cloudReady, setCloudReady] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const applies = camera.problem_kind === PRIVATE_NETWORK;

  useEffect(() => {
    if (!applies) return;
    cached("connection-options", connectionOptions, OPTIONS_MAX_AGE_MS)
      .then((options) => setCloudReady(options.imou_cloud))
      .catch(() => setCloudReady(false));
  }, [applies]);

  if (!applies || !cloudReady) return null;

  async function switchToCloud() {
    setPending(true);
    setMessage(null);
    try {
      // Sin red local: el servidor no la alcanza. Va directo a la nube de Imou.
      const result = await autoConnect(camera.establishment_id, null, "admin", "");
      if (result.added.length > 0 || result.already > 0) {
        await setCameraEnabled(camera.id, false);
        onDone();
        return;
      }
      const cloud = result.attempts.find((attempt) => attempt.method === "nube_imou");
      setMessage(cloud?.detail ?? "La nube de Imou no devolvió cámaras en línea.");
    } catch (failure) {
      setMessage(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={styles.caja}>
      <button type="button" className={styles.boton} disabled={pending} onClick={switchToCloud}>
        {pending ? "Conectando por la nube de Imou…" : "Conectar por la nube de Imou"}
      </button>
      {message && (
        <p className={styles.mensaje} role="alert">
          {message}
        </p>
      )}
    </div>
  );
}
