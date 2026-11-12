import { AppShell } from "@/components/AppShell";
import styles from "./incidentes.module.css";

/** Se ve al instante al hacer clic, mientras el servidor trae los eventos. */
export default function Loading() {
  return (
    <AppShell>
      <main className={styles.pagina} aria-busy="true">
        <p className={styles.tenue} role="status">
          Cargando eventos…
        </p>
      </main>
    </AppShell>
  );
}
