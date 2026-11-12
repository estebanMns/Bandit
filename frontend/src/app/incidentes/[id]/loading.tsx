import { AppShell } from "@/components/AppShell";
import styles from "../incidentes.module.css";

/** Se ve al instante al abrir un evento, mientras el servidor lo trae. */
export default function Loading() {
  return (
    <AppShell>
      <main className={styles.pagina} aria-busy="true">
        <p className={styles.tenue} role="status">
          Cargando el evento…
        </p>
      </main>
    </AppShell>
  );
}
