"use client";

import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import {
  createCamera,
  deleteCamera,
  listCameras,
  setCameraEnabled,
  type Camera,
} from "@/features/cameras/api";
import { CameraFinder } from "@/features/cameras/CameraFinder";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { ApiError } from "@/lib/api";
import styles from "../ajustes.module.css";

export default function CamerasPage() {
  const { current, loading } = useEstablishment();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!current) return;
    listCameras(current.id)
      .then(setCameras)
      .catch(() => setCameras([]));
  }, [current]);

  async function run(action: () => Promise<unknown>) {
    if (!current) return;
    setError(null);
    try {
      await action();
      setCameras(await listCameras(current.id));
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
    }
  }

  function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    void run(async () => {
      await createCamera(current!.id, String(data.get("name")), String(data.get("url")));
      form.reset();
    });
  }

  return (
    <AppShell>
      <main className={styles.pagina}>
        <h1 className={styles.titulo}>Cámaras</h1>

        {!loading && !current && <p>Crea primero tu local en la sección Local.</p>}

        {current && (
          <section className={`vidrio ${styles.seccion}`}>
            <h2>Buscar cámaras en tu red</h2>
            <p className={styles.ayuda}>
              Bandit revisa los equipos de tu Wi-Fi, prueba las rutas de video conocidas de cada
              marca y, si ninguna funciona, le pide a Gemini otras para probar. La clave nunca se
              envía a la IA.
            </p>
            <CameraFinder
              establishmentId={current.id}
              onAdded={() => void listCameras(current.id).then(setCameras)}
            />
          </section>
        )}

        {current && (
          <section className={`vidrio ${styles.seccion}`}>
            <h2>Agregar cámara a mano</h2>
            <form className={styles.formulario} onSubmit={add}>
              <Field label="Nombre" name="name" placeholder="Barra principal" required />
              <Field
                label="Dirección de la cámara"
                name="url"
                type="password"
                autoComplete="off"
                hint="rtsp:// en la red local, o imou://<número de serie>/<canal>?stream=1 para una cámara Imou por su nube. Se guarda cifrada y no se vuelve a mostrar."
                required
                error={error}
              />
              <Button type="submit">Agregar cámara</Button>
            </form>
          </section>
        )}

        {cameras.length > 0 && (
          <section className={`vidrio ${styles.seccion}`}>
            <h2>Cámaras de {current?.name}</h2>
            <ul className={styles.lista}>
              {cameras.map((camera) => (
                <li key={camera.id} className={styles.fila}>
                  <strong>{camera.name}</strong>
                  <Button
                    variant="secundario"
                    onClick={() => run(() => setCameraEnabled(camera.id, !camera.enabled))}
                  >
                    {camera.enabled ? "Pausar" : "Reanudar"}
                  </Button>
                  <Button variant="secundario" onClick={() => run(() => deleteCamera(camera.id))}>
                    Eliminar
                  </Button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </AppShell>
  );
}
