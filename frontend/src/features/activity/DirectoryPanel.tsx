"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { formatReward } from "@/features/directory/priority";
import type { WantedRecord } from "@/features/directory/types";
import { formatDateTime } from "@/features/incidents/labels";
import { ApiError } from "@/lib/api";
import { getSyncStatus, listWanted, startSync } from "./api";
import styles from "./activity.module.css";
import { triggerLabel } from "./labels";
import type { SyncStatus } from "./types";

const POLL_MS = 5000;
const PREVIEW = 12;

/**
 * Lo que Gemini extrajo de la página de los más buscados. Es solo consulta:
 * nunca se compara con el video de las cámaras.
 */
export function DirectoryPanel() {
  const [records, setRecords] = useState<WantedRecord[]>([]);
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [nextRecords, nextStatus] = await Promise.all([listWanted(), getSyncStatus()]);
    setRecords(nextRecords);
    setStatus(nextStatus);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh().catch(() => setMessage("No se pudo leer el directorio."));
  }, [refresh]);

  useEffect(() => {
    if (!status?.running) return;
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [status?.running, refresh]);

  async function extract() {
    setMessage(null);
    try {
      setStatus(await startSync());
    } catch (failure) {
      setMessage(
        failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.",
      );
    }
  }

  const last = status?.runs[0];

  return (
    <section className={`vidrio ${styles.seccion}`} aria-labelledby="titulo-directorio">
      <div className={styles.encabezado}>
        <div>
          <h2 id="titulo-directorio">Los más buscados</h2>
          <p className={styles.detalle}>
            Gemini lee la página pública de la Policía Nacional y extrae nombre, delito, recompensa
            y foto. Es solo de consulta: el video de tus cámaras nunca se compara con estas fotos.
          </p>
        </div>
        <Button variant="secundario" onClick={extract} disabled={status?.running}>
          {status?.running ? "Extrayendo…" : "Extraer ahora"}
        </Button>
      </div>

      <p className={styles.detalle} role="status">
        {status?.running &&
          "Gemini está leyendo la página de la Policía. Puede tardar unos minutos. "}
        {last &&
          !status?.running &&
          `Última extracción ${triggerLabel(last.trigger)}: ${formatDateTime(last.started_at)}. ` +
            (last.completed
              ? `${last.published} publicados, ${last.rejected} rechazados por no coincidir con la fuente.`
              : last.error
                ? `Falló (${last.error}).`
                : "No terminó; el directorio quedó como estaba.")}
        {!status && !message && "Cargando el estado de la extracción…"}
        {status && !last && !status.running && "Todavía no se ha hecho ninguna extracción."}
        {message && ` ${message}`}
      </p>

      {records.length > 0 && (
        <>
          <ul className={styles.galeria}>
            {records.slice(0, PREVIEW).map((record) => (
              <li key={record.slug}>
                <Link href={`/directorio/${record.slug}`}>
                  {record.photo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={record.photo_url} alt="" loading="lazy" />
                  ) : (
                    <span className={styles.sinFoto}>Sin foto</span>
                  )}
                  <strong>{record.name}</strong>
                  <span className={styles.detalle}>{formatReward(record)}</span>
                  {record.crime && <span className={styles.detalle}>{record.crime}</span>}
                </Link>
              </li>
            ))}
          </ul>
          <Link href="/directorio" className={styles.enlace}>
            Ver los {records.length} registros del directorio
          </Link>
        </>
      )}
    </section>
  );
}
