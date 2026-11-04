"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";
import styles from "@/app/ajustes/ajustes.module.css";

const PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";

function keyToBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="));
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export function PushToggle({ establishmentId }: { establishmentId: string }) {
  const [state, setState] = useState<"inactivo" | "activando" | "activo">("inactivo");
  const [error, setError] = useState<string | null>(null);

  if (!PUBLIC_KEY) return null;

  async function enable() {
    setState("activando");
    setError(null);
    try {
      if ((await Notification.requestPermission()) !== "granted") {
        throw new Error("Permite las notificaciones en tu navegador para activarlas.");
      }
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: keyToBytes(PUBLIC_KEY),
      });
      await api(`/api/establishments/${establishmentId}/push-subscriptions`, {
        method: "POST",
        body: JSON.stringify(subscription.toJSON()),
      });
      setState("activo");
    } catch (failure) {
      setState("inactivo");
      const known = failure instanceof ApiError || failure instanceof Error;
      setError(known ? failure.message : "No se pudieron activar las notificaciones.");
    }
  }

  return (
    <section className={styles.seccion}>
      <h2>Alertas con la app cerrada</h2>
      <p className={styles.ayuda}>Recibe en este dispositivo un aviso de cada detección.</p>
      {state === "activo" ? (
        <p className={styles.confirmacion} role="status">
          Notificaciones activadas en este dispositivo.
        </p>
      ) : (
        <div className={styles.formulario}>
          <Button variant="secundario" disabled={state === "activando"} onClick={enable}>
            Activar notificaciones
          </Button>
        </div>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
