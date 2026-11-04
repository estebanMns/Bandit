import type { Metadata } from "next";
import { fetchDirectory } from "@/features/directory/data";
import { DirectoryBrowser } from "@/features/directory/DirectoryBrowser";
import styles from "@/features/directory/directory.module.css";

export const metadata: Metadata = {
  title: "Directorio",
  description: "Copia informativa del listado público de la Policía Nacional.",
};

/** ISR: se regenera tras cada extracción y, como respaldo, cada hora. */
export const revalidate = 3600;

const SOURCE = "https://www.policia.gov.co/los-mas-buscados-colombia";

export default async function DirectoryPage() {
  const records = await fetchDirectory();

  return (
    <main className={styles.pagina}>
      <h1 className={styles.titulo}>Los más buscados</h1>
      <p className={styles.aviso}>
        Copia informativa del <a href={SOURCE}>listado público de la Policía Nacional</a>. Toda
        persona se presume inocente mientras no se demuestre lo contrario. Si crees reconocer a
        alguien, no intervengas: usa la línea oficial de la ficha o llama al 123.
      </p>
      {records === null ? (
        <p>El directorio no está disponible en este momento. Consulta la fuente oficial.</p>
      ) : records.length === 0 ? (
        <p>Aún no hay registros. Aparecerán después de la primera extracción.</p>
      ) : (
        <DirectoryBrowser records={records} />
      )}
    </main>
  );
}
