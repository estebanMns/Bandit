"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api";
import { confirmIncident, discardIncident } from "./api";
import { formatTime, situationLabel, STATUS_LABELS } from "./labels";
import type { Incident } from "./types";
import styles from "./DecisionPanel.module.css";

interface DecisionPanelProps {
  incident: Incident | null;
  caiNumber: string | null;
  onChange: (incident: Incident) => void;
}

const FAILURE_MESSAGE = "No hay conexión con el servidor.";

export function DecisionPanel({ incident, caiNumber, onChange }: DecisionPanelProps) {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function act(action: (id: string) => Promise<Incident>) {
    if (!incident) return;
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

  if (!incident) {
    return (
      <aside className={styles.panel} aria-label="Decisión">
        <h2 className={styles.calma}>Todo en calma</h2>
        <p className={styles.tenue}>Cuando una cámara detecte algo, lo verás aquí para decidir.</p>
        <EmergencyCall />
      </aside>
    );
  }

  const canConfirm =
    incident.status === "detected" || incident.status === "notification_failed";
  const canDiscard = incident.status === "detected";

  return (
    <aside className={styles.panel} aria-label="Decisión" aria-live="assertive">
      <div className={styles.encabezado} data-estado={incident.status}>
        <h2>{situationLabel(incident.type)}</h2>
        <p>
          {incident.camera_name} a las {formatTime(incident.detected_at)}
        </p>
      </div>

      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className={styles.evidencia}
        src={`/api/incidents/${incident.id}/evidence`}
        alt={`Fotograma de ${incident.camera_name}: ${incident.description}`}
      />
      <p>{incident.description}</p>
      <p className={styles.estado}>{STATUS_LABELS[incident.status]}</p>

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
                {incident.status === "detected" ? "Confirmar y avisar al CAI" : "Reintentar aviso"}
              </Button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className={styles.velo} />
              <Dialog.Content className={styles.dialogo}>
                <Dialog.Title>¿Avisar al CAI?</Dialog.Title>
                <Dialog.Description>
                  Se enviará un WhatsApp a {caiNumber} con la dirección del local y esta
                  descripción. Confirma solo si viste la situación en el video.
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
            Descartar
          </Button>
        )}
      </div>
      <EmergencyCall />
    </aside>
  );
}

function EmergencyCall() {
  return (
    <a className={styles.linea} href="tel:123">
      Llama al 123
    </a>
  );
}
