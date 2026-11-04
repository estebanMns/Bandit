import type { Metadata } from "next";
import Link from "next/link";
import styles from "../ingresar/page.module.css";

export const metadata: Metadata = { title: "Sin conexión" };

export default function OfflinePage() {
  return (
    <main className={styles.pagina}>
      <h1 className={styles.titulo}>No hay conexión</h1>
      <p className={styles.bajada}>
        El video y las alertas necesitan internet. Si hay una emergencia, llama al 123.
      </p>
      <p>
        <a href="tel:123">Llama al 123</a>
      </p>
      <p>
        <Link href="/directorio">Abrir el directorio guardado</Link>
      </p>
    </main>
  );
}
