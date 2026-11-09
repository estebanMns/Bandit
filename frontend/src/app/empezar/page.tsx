"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { createCamera, listCameras, type Camera } from "@/features/cameras/api";
import { CameraFinder } from "@/features/cameras/CameraFinder";
import { createEstablishment, setCaiWhatsApp } from "@/features/establishments/api";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { firstPending, steps, type StepId } from "@/features/onboarding/setup";
import { ApiError } from "@/lib/api";
import styles from "./empezar.module.css";

function message(failure: unknown): string {
  return failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.";
}

/** CSR: asistente de primer ingreso. Cada paso se marca solo cuando ya está hecho. */
export default function StartPage() {
  const router = useRouter();
  const { current, loading, reload } = useEstablishment();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [chosen, setChosen] = useState<StepId | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadCameras = useCallback(async () => {
    if (current) setCameras(await listCameras(current.id));
  }, [current]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCameras();
  }, [loadCameras]);

  const state = {
    hasLocal: Boolean(current),
    hasCai: Boolean(current?.cai_whatsapp),
    cameraCount: cameras.length,
  };
  const list = steps(state);
  const active = chosen ?? firstPending(state);

  async function run(action: () => Promise<unknown>, next?: StepId) {
    setError(null);
    try {
      await action();
      await reload();
      await loadCameras();
      if (next) setChosen(next);
    } catch (failure) {
      setError(message(failure));
    }
  }

  function createLocal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void run(
      () => createEstablishment(String(data.get("name")), String(data.get("address"))),
      "cai",
    );
  }

  function saveCai(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const number = String(new FormData(event.currentTarget).get("number")).trim();
    void run(() => setCaiWhatsApp(current!.id, number || null), "camaras");
  }

  function addManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    void run(async () => {
      await createCamera(current!.id, String(data.get("name")), String(data.get("url")));
      form.reset();
    });
  }

  function later() {
    router.push("/panel");
  }

  return (
    <AppShell>
      <main className={styles.pagina}>
        <header className={styles.cabecera}>
          <p className={styles.eyebrow}>Primeros pasos</p>
          <h1>Deja Bandit listo para tu turno</h1>
          <p className={styles.bajada}>
            Cuatro pasos y empiezas a vigilar. Puedes volver aquí cuando quieras desde el Panel.
          </p>
        </header>

        <div className={styles.cuerpo}>
          <nav aria-label="Pasos" className={styles.pasos}>
            <ol>
              {list.map((step, index) => (
                <li key={step.id}>
                  <button
                    type="button"
                    className={styles.paso}
                    aria-current={active === step.id ? "step" : undefined}
                    data-hecho={step.done}
                    onClick={() => setChosen(step.id)}
                  >
                    <span className={styles.numero} aria-hidden="true">
                      {step.done ? "✓" : index + 1}
                    </span>
                    <span>
                      {step.title}
                      <span className={styles.estado}>
                        {step.done ? "Hecho" : step.optional ? "Opcional" : "Pendiente"}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </nav>

          <section className={styles.contenido} aria-live="polite">
            {loading && <p>Cargando tu cuenta…</p>}

            {!loading && active === "local" && (
              <>
                <h2>Tu local</h2>
                {current ? (
                  <p>
                    <strong>{current.name}</strong> · {current.address}
                  </p>
                ) : (
                  <form className={styles.formulario} onSubmit={createLocal}>
                    <Field label="Nombre del local" name="name" required />
                    <Field
                      label="Dirección"
                      name="address"
                      hint="Es la dirección que recibirá el CAI en cada alerta."
                      required
                      error={error}
                    />
                    <Button type="submit">Guardar y seguir</Button>
                  </form>
                )}
                {current && <Button onClick={() => setChosen("cai")}>Seguir</Button>}
              </>
            )}

            {!loading && active === "cai" && current && (
              <>
                <h2>WhatsApp del CAI más cercano</h2>
                <p className={styles.ayuda}>
                  Cuando confirmes una alerta, Bandit le escribe a este número con la dirección del
                  local. Acuerda su uso con el CAI antes de registrarlo.
                </p>
                <form key={current.cai_whatsapp} className={styles.formulario} onSubmit={saveCai}>
                  <Field
                    label="Número de WhatsApp"
                    name="number"
                    type="tel"
                    inputMode="tel"
                    placeholder="+57 300 123 4567"
                    defaultValue={current.cai_whatsapp ?? ""}
                    hint="Incluye el indicativo del país."
                    error={error}
                  />
                  <div className={styles.acciones}>
                    <Button type="submit">Guardar y seguir</Button>
                    <Button variant="secundario" onClick={() => setChosen("camaras")}>
                      Lo configuro después
                    </Button>
                  </div>
                </form>
              </>
            )}

            {!loading && active === "camaras" && current && (
              <>
                <h2>Conecta tu primera cámara</h2>
                <p className={styles.ayuda}>
                  Busca las cámaras de tu Wi-Fi y conéctalas con su clave. Si ninguna ruta conocida
                  funciona, Gemini propone otras para probar; la clave nunca se le envía.
                </p>
                <CameraFinder establishmentId={current.id} onAdded={() => void loadCameras()} />

                <details className={styles.manual}>
                  <summary>Tengo la dirección de la cámara</summary>
                  <form className={styles.formulario} onSubmit={addManual}>
                    <Field label="Nombre" name="name" placeholder="Barra principal" required />
                    <Field
                      label="Dirección de la cámara"
                      name="url"
                      type="password"
                      autoComplete="off"
                      hint="rtsp://… en tu red, o imou://<número de serie>/<canal> por la nube de Imou."
                      required
                      error={error}
                    />
                    <Button type="submit">Agregar cámara</Button>
                  </form>
                </details>

                {cameras.length > 0 && (
                  <>
                    <p role="status">
                      {cameras.length === 1
                        ? "Tienes 1 cámara registrada."
                        : `Tienes ${cameras.length} cámaras registradas.`}
                    </p>
                    <Button onClick={() => setChosen("listo")}>Seguir</Button>
                  </>
                )}
              </>
            )}

            {!loading && active === "listo" && (
              <>
                <h2>{list[3]!.done ? "Todo listo" : "Casi listo"}</h2>
                <p className={styles.ayuda}>
                  {list[3]!.done
                    ? "Gemini ya vigila tus cámaras. Cuando vea algo, te aviso en el Monitor y tú decides."
                    : "Te falta al menos una cámara. Puedes agregarla ahora o más tarde."}
                </p>
                <div className={styles.acciones}>
                  <Link href="/panel" className={styles.botonEnlace}>
                    Ir al Panel
                  </Link>
                  <Link href="/actividad" className={styles.enlace}>
                    Ver qué hace la IA
                  </Link>
                  <Link href="/directorio" className={styles.enlace}>
                    Ver los más buscados
                  </Link>
                </div>
              </>
            )}

            {!loading && active !== "listo" && (
              <button type="button" className={styles.despues} onClick={later}>
                Lo hago después
              </button>
            )}
          </section>
        </div>
      </main>
    </AppShell>
  );
}
