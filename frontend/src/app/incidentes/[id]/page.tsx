import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { formatDateTime, situationLabel, STATUS_LABELS } from "@/features/incidents/labels";
import type { Incident } from "@/features/incidents/types";
import { serverApi } from "@/lib/server-api";
import styles from "../incidentes.module.css";

export const metadata: Metadata = { title: "Detalle del incidente" };

export default async function IncidentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const incident = await serverApi<Incident>(`/api/incidents/${encodeURIComponent(id)}`);

  return (
    <AppShell>
      <main className={styles.pagina}>
        <Link href="/incidentes">Volver a incidentes</Link>
        <h1 className={styles.titulo}>{situationLabel(incident.type)}</h1>
        <div className={styles.detalle}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className={styles.evidencia}
            src={`/api/incidents/${incident.id}/evidence`}
            alt={`Fotograma de ${incident.camera_name}: ${incident.description}`}
          />
          <div>
            <p>{incident.description}</p>
            <p className={styles.tenue}>
              {incident.camera_name}, {formatDateTime(incident.detected_at)}
            </p>
            <h2>Registro</h2>
            <ol className={styles.bitacora}>
              {incident.audit.map((entry) => (
                <li key={`${entry.status}-${entry.at}`}>
                  <strong>{STATUS_LABELS[entry.status]}</strong>
                  <span className={styles.tenue}>
                    {formatDateTime(entry.at)}, {entry.actor}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </main>
    </AppShell>
  );
}
