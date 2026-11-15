"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { PasswordField } from "@/components/ui/PasswordField";
import { ApiError } from "@/lib/api";
import { cached } from "@/lib/cache";
import { connectImou, connectionOptions, type ImouConnectResult } from "./api";
import styles from "./ImouConnectForm.module.css";

const OPTIONS_MAX_AGE_MS = 5 * 60_000;

interface ImouConnectFormProps {
  establishmentId: string;
  onConnected: (result: ImouConnectResult) => void;
}

function summary(result: ImouConnectResult): string {
  const added = result.added.length;
  if (added === 0) return "Esa cámara ya estaba conectada.";
  return added === 1 ? "Listo: se conectó 1 cámara." : `Listo: se conectaron ${added} lentes.`;
}

/**
 * Cualquier cliente conecta su cámara Imou por internet con dos datos de la etiqueta: el número
 * de serie (S/N) y la clave o código de seguridad. No hace falta estar en la misma red.
 */
export function ImouConnectForm({ establishmentId, onConnected }: ImouConnectFormProps) {
  const [available, setAvailable] = useState<boolean | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    cached("connection-options", connectionOptions, OPTIONS_MAX_AGE_MS)
      .then((options) => setAvailable(options.imou_cloud))
      .catch(() => setAvailable(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setPending(true);
    setError(null);
    setDone(null);
    try {
      const result = await connectImou(
        establishmentId,
        String(data.get("serial") ?? ""),
        String(data.get("code") ?? ""),
      );
      form.reset();
      setDone(summary(result));
      onConnected(result);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
    } finally {
      setPending(false);
    }
  }

  if (available === false) {
    return (
      <p className={styles.ayuda}>
        Este servidor todavía no tiene activada la conexión por la nube de Imou.
      </p>
    );
  }

  return (
    <form className={styles.formulario} onSubmit={submit}>
      <p className={styles.ayuda}>
        Los dos datos están en la etiqueta de la cámara o en su caja. La cámara debe estar
        encendida y con internet (configúrala primero con la app Imou Life).
      </p>
      <div className={styles.fila}>
        <Field
          label="Número de serie (S/N)"
          name="serial"
          placeholder="9F0A1B2C3D4E5"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          required
          minLength={6}
          maxLength={64}
        />
        <PasswordField
          label="Clave o código de seguridad"
          name="code"
          autoComplete="off"
          hint="El código de la etiqueta (SC), o la clave nueva si la cambiaste en Imou Life."
          maxLength={200}
        />
      </div>
      <Button type="submit" disabled={pending || available === null}>
        {pending ? "Conectando…" : "Conectar cámara"}
      </Button>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {done && (
        <p className={styles.ok} role="status">
          {done}
        </p>
      )}
    </form>
  );
}
