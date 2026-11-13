"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api";
import { confirmIncident, discardIncident } from "./api";
import { decisionTexts } from "./labels";
import type { Incident } from "./types";
import styles from "./DecisionPanel.module.css";

const FAILURE_MESSAGE = "No hay conexión con el servidor.";

interface DecisionActionsProps {
  incident: Incident;
  caiNumber: string | null;
  onChange: (incident: Incident) => void;
}

/**
 * Aceptar (avisa al CAI, tras confirmarlo en un diálogo) o rechazar una detección.
 * Es el único camino hacia un aviso: Bandit nunca avisa al CAI por su cuenta.
 */
export function DecisionActions({ incident, caiNumber, onChange }: DecisionActionsProps) {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const texts = decisionTexts(incident.type);

  async function act(action: (id: string) => Promise<Incident>) {
    setPending(true);
    setError(null);
    try {
      onChange(await action(incident.id));
      setConfirming(false);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : FAILURE_MESSAGE);
    } finally {
      setPending(false);
    }
  }

  const canConfirm = incident.status === "detected" || incident.status === "notification_failed";
  const canDiscard = incident.status === "detected";
  if (!canConfirm && !canDiscard) return null;

  return (
    <>
      {canConfirm && !caiNumber && (
        <p className={styles.tenue}>
          Para avisar por WhatsApp, <Link href="/ajustes/local">agrega el número del CAI</Link>.
        </p>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <div className={styles.acciones}>
        {canConfirm && (
          <Dialog.Root open={confirming} onOpenChange={setConfirming}>
            <Dialog.Trigger asChild>
              <Button variant="peligro" disabled={!caiNumber || pending}>
                {incident.status === "detected" ? texts.confirm : "Reintentar aviso"}
              </Button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className={styles.velo} />
              <Dialog.Content className={styles.dialogo}>
                <Dialog.Title>{texts.question}</Dialog.Title>
                <Dialog.Description>
                  Se enviará un WhatsApp a {caiNumber} con la dirección del local y esta
                  descripción. {texts.check}
                </Dialog.Description>
                <div className={styles.acciones}>
                  <Button
                    variant="peligro"
                    disabled={pending}
                    onClick={() => act(confirmIncident)}
                  >
                    {pending ? "Enviando" : "Sí, avisar al CAI"}
                  </Button>
                  <Dialog.Close asChild>
                    <Button variant="secundario">Volver</Button>
                  </Dialog.Close>
                </div>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        )}
        {canDiscard && (
          <Button variant="secundario" disabled={pending} onClick={() => act(discardIncident)}>
            {texts.discard}
          </Button>
        )}
      </div>
    </>
  );
}
