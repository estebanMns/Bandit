"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { PasswordField } from "@/components/ui/PasswordField";
import { ApiError } from "@/lib/api";
import { autoConnect, connectionOptions, type AutoConnectResult } from "./api";
import styles from "./AutoConnectCard.module.css";

const METHOD: Record<string, string> = {
  red_local: "Red local (Wi-Fi)",
  nube_imou: "Nube de Imou",
};

const OK = new Set(["conectada"]);
const NEUTRAL = new Set(["omitido"]);

interface AutoConnectCardProps {
  establishmentId: string;
  onConnected: () => void;
}

/** Un botón: Bandit prueba la red local y, si no alcanza, la nube de Imou. */
export function AutoConnectCard({ establishmentId, onConnected }: AutoConnectCardProps) {
  const [cloudReady, setCloudReady] = useState<boolean | null>(null);
  const [result, setResult] = useState<AutoConnectResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    connectionOptions()
      .then((options) => setCloudReady(options.imou_cloud))
      .catch(() => setCloudReady(false));
  }, []);

  async function connect(network: string | null, username: string, password: string) {
    setPending(true);
    setError(null);
    try {
      const outcome = await autoConnect(establishmentId, network, username, password);
      setResult(outcome);
      if (outcome.added.length > 0) onConnected();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
    } finally {
      setPending(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await connect(
      String(data.get("network") || "") || null,
      String(data.get("username") || "admin"),
      String(data.get("password") || ""),
    );
  }

  const needsCloud = result?.attempts.some(
    (attempt) => attempt.method === "nube_imou" && attempt.status === "sin_configurar",
  );

  return (
    <div className={styles.tarjeta}>
      <form className={styles.formulario} onSubmit={submit}>
        <Field
          label="Red de tu Wi-Fi"
          name="network"
          defaultValue="192.168.1.0/24"
          hint="Déjala así si la IP de tu computador empieza por 192.168.1."
        />
        <div className={styles.fila}>
          <Field label="Usuario" name="username" defaultValue="admin" autoComplete="off" />
          <PasswordField
            label="Clave o código de la etiqueta"
            name="password"
            autoComplete="off"
            hint="Solo para la red local. Nunca se envía a la IA."
          />
        </div>
        <Button type="submit" disabled={pending}>
          {pending
            ? "Buscando y conectando… (hasta un minuto)"
            : "Conectar mi cámara automáticamente"}
        </Button>
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        {cloudReady === true && (
          <>
            <p className={styles.nota}>
              La nube de Imou está configurada: se usará si la red local falla.
            </p>
            {/* Desde un servidor en internet la red local no sirve: se va directo a la nube. */}
            <Button
              type="button"
              variant="secundario"
              disabled={pending}
              onClick={() => void connect(null, "admin", "")}
            >
              Conectar por la nube de Imou
            </Button>
            <p className={styles.ayuda}>
              Úsalo si Bandit corre en la nube (por ejemplo Render) o si la cámara está en otra
              red: trae las cámaras de tu cuenta Imou sin clave ni búsqueda en el Wi-Fi.
            </p>
          </>
        )}
      </form>

      {result && (
        <div className={styles.resultado} role="status">
          <p className={styles.titulo}>
            {result.connected
              ? result.added.length > 0
                ? `Listo: ${result.added.length === 1 ? "se agregó 1 cámara" : `se agregaron ${result.added.length} cámaras`}.`
                : "Tus cámaras ya estaban conectadas."
              : "Todavía no se pudo conectar la cámara."}
          </p>
          <ol className={styles.intentos}>
            {result.attempts.map((attempt) => (
              <li
                key={attempt.method}
                data-estado={
                  OK.has(attempt.status) ? "ok" : NEUTRAL.has(attempt.status) ? "neutro" : "fallo"
                }
              >
                <strong>{METHOD[attempt.method] ?? attempt.method}</strong>
                <span>{attempt.detail}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {(needsCloud || cloudReady === false) && !result?.connected && (
        <details className={styles.guia} open={Boolean(needsCloud)}>
          <summary>Si la cámara no responde en tu red: conéctala por la nube de Imou</summary>
          <ol>
            <li>
              Entra a{" "}
              <a href="https://open.imoulife.com" target="_blank" rel="noreferrer">
                open.imoulife.com
              </a>{" "}
              con la misma cuenta de la app Imou Life.
            </li>
            <li>
              Crea una aplicación y copia su <strong>App ID</strong> y <strong>App Secret</strong>.
            </li>
            <li>
              Ponlos en el archivo <code>.env</code> como <code>IMOU_APP_ID</code> e{" "}
              <code>IMOU_APP_SECRET</code> y reinicia con <code>docker compose up -d backend</code>.
            </li>
            <li>Vuelve aquí y pulsa el botón otra vez: Bandit encontrará tus cámaras solo.</li>
          </ol>
        </details>
      )}
    </div>
  );
}
