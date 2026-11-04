import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchWanted } from "@/features/directory/data";
import styles from "@/features/directory/directory.module.css";

interface PageProps {
  params: Promise<{ slug: string }>;
}

/** ISR bajo demanda: cada ficha se genera en su primer pedido. */
export const revalidate = 60;
export const dynamicParams = true;

export function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const record = await fetchWanted((await params).slug);
  return { title: record?.name ?? "Registro" };
}

const COLOMBIA_DATE = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "long",
  timeZone: "America/Bogota",
});

export default async function WantedPage({ params }: PageProps) {
  const record = await fetchWanted((await params).slug);
  if (!record) notFound();

  const facts: [string, string | null][] = [
    ["Alias", record.alias],
    ["Delito publicado", record.crime],
    ["Región", record.region],
    ["Recompensa", record.reward],
  ];

  return (
    <main className={styles.pagina}>
      <Link href="/directorio">Volver al directorio</Link>
      <div className={styles.detalle}>
        {record.photo_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={record.photo_url} alt={`Foto publicada de ${record.name}`} className={styles.foto} />
        )}
        <div className={styles.pagina}>
          <h1 className={styles.titulo}>{record.name}</h1>
          <dl className={styles.datos}>
            {facts.map(([label, value]) =>
              value ? (
                <div key={label} style={{ display: "contents" }}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ) : null,
            )}
          </dl>

          <section className={styles.reporte} aria-label="Cómo reportar">
            <h2>Si crees reconocer a esta persona</h2>
            <p>No intervengas ni la confrontes. Avisa por un canal oficial.</p>
            {record.hotline_phones.map((phone) => (
              <a key={phone} href={`tel:${phone}`}>
                Línea directa {phone}
              </a>
            ))}
            {record.hotline_email && (
              <a href={`mailto:${record.hotline_email}`}>{record.hotline_email}</a>
            )}
            <a href="tel:123">Llama al 123</a>
          </section>

          <p className={styles.tenue}>
            Fuente: <a href={record.source_url}>Policía Nacional de Colombia</a>
            {record.last_seen_at &&
              `, verificado el ${COLOMBIA_DATE.format(new Date(record.last_seen_at))}`}
            . Se presume inocente mientras no se demuestre lo contrario.
          </p>
          {record.flyer_url && <a href={record.flyer_url}>Ver volante oficial (PDF)</a>}
        </div>
      </div>
    </main>
  );
}
