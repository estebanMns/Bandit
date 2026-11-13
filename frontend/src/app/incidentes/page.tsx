import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import type { Establishment } from "@/features/establishments/api";
import { formatDateTime, situationLabel, statusLabel } from "@/features/incidents/labels";
import type { Incident } from "@/features/incidents/types";
import { serverApi } from "@/lib/server-api";
import styles from "./incidentes.module.css";

export const metadata: Metadata = { title: "Incidentes" };

/** SSR: los datos dependen de la sesión y deben estar al día en cada visita. */
export default async function IncidentsPage({
  searchParams,
}: {
  searchParams: Promise<{ local?: string }>;
}) {
  const { local } = await searchParams;
  const establishments = await serverApi<Establishment[]>("/api/establishments");
  const current = establishments.find((item) => item.id === local) ?? establishments[0];
  const incidents = current
    ? await serverApi<Incident[]>(`/api/establishments/${current.id}/incidents`)
    : [];

  return (
    <AppShell>
      <main className={styles.pagina}>
        <h1 className={styles.titulo}>Incidentes{current ? ` de ${current.name}` : ""}</h1>
        {incidents.length === 0 ? (
          <p className={styles.tenue}>
            No hay incidentes registrados. Las detecciones aparecerán aquí para que las revises.
          </p>
        ) : (
          <ol className={styles.lista}>
            {incidents.map((incident) => (
              <li key={incident.id}>
                <Link href={`/incidentes/${incident.id}`} className={styles.fila}>
                  <span className={styles.situacion}>{situationLabel(incident.type)}</span>
                  <span className={styles.tenue}>{incident.camera_name}</span>
                  <time dateTime={incident.detected_at} className={styles.tenue}>
                    {formatDateTime(incident.detected_at)}
                  </time>
                  <span className={styles.estado} data-estado={incident.status}>
                    {statusLabel(incident.type, incident.status)}
                  </span>
                  {incident.status === "detected" && (
                    <span className={styles.revisar} aria-hidden="true">
                      Revisar →
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ol>
        )}
      </main>
    </AppShell>
  );
}
