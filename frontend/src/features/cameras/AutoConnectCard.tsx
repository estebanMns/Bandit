"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { PasswordField } from "@/components/ui/PasswordField";
import { ApiError } from "@/lib/api";
import { autoConnect, type AutoConnectResult } from "./api";
import { ImouConnectForm } from "./ImouConnectForm";
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

/**
 * Lo normal: la cámara Imou con su número de serie y su clave, por internet. Si Bandit está en
 * el mismo Wi-Fi que la cámara, también puede buscarla en la red.
 */
export function AutoConnectCard({ establishmentId, onConnected }: AutoConnectCardProps) {
  const [result, setResult] = useState<AutoConnectResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className={styles.tarjeta}>
      <h3 className={styles.titulo}>Cámara Imou por internet</h3>
      <ImouConnectForm
        establishmentId={establishmentId}
        onConnected={(outcome) => {
          if (outcome.added.length > 0) onConnected();
        }}
      />

      <details className={styles.guia}>
        <summary>¿Bandit está en el mismo Wi-Fi que la cámara? Búscala en la red</summary>
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
        </form>
      </details>

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
    </div>
  );
}
