"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";
import styles from "@/app/ajustes/ajustes.module.css";

export function WhatsAppTest({ establishmentId }: { establishmentId: string }) {
  const [state, setState] = useState<"inactivo" | "enviando" | "enviado">("inactivo");
  const [error, setError] = useState<string | null>(null);

  async function send() {
    setState("enviando");
    setError(null);
    try {
      await api(`/api/establishments/${establishmentId}/whatsapp-test`, { method: "POST" });
      setState("enviado");
    } catch (failure) {
      setState("inactivo");
      setError(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
    }
  }

  return (
    <div className={styles.formulario}>
      <Button variant="secundario" disabled={state === "enviando"} onClick={send}>
        {state === "enviando" ? "Enviando" : "Enviar mensaje de prueba"}
      </Button>
      {state === "enviado" && (
        <p className={styles.confirmacion} role="status">
          Mensaje de prueba enviado.
        </p>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
