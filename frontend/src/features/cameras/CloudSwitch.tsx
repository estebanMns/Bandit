"use client";

import { useState } from "react";
import { setCameraEnabled, type Camera, type ImouConnectResult } from "./api";
import { ImouConnectForm } from "./ImouConnectForm";
import styles from "./CloudSwitch.module.css";

const PRIVATE_NETWORK = "private_network";

/**
 * Cuando el servidor no alcanza una cámara de una red privada (por ejemplo el backend en la
 * nube y la cámara en el Wi-Fi del local), la conecta por la nube de Imou con su número de serie
 * y su clave, y pausa la vieja.
 */
export function CloudSwitch({ camera, onDone }: { camera: Camera; onDone: () => void }) {
  const [open, setOpen] = useState(false);

  if (camera.problem_kind !== PRIVATE_NETWORK) return null;

  async function connected(result: ImouConnectResult) {
    if (result.added.length > 0 || result.already > 0) {
      await setCameraEnabled(camera.id, false).catch(() => undefined);
      onDone();
    }
  }

  return (
    <div className={styles.caja}>
      {open ? (
        <div className={styles.panel}>
          <ImouConnectForm establishmentId={camera.establishment_id} onConnected={connected} />
        </div>
      ) : (
        <button type="button" className={styles.boton} onClick={() => setOpen(true)}>
          Conectar por la nube de Imou
        </button>
      )}
    </div>
  );
}
