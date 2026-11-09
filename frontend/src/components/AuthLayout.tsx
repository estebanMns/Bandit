import Link from "next/link";
import type { ReactNode } from "react";
import styles from "./AuthLayout.module.css";

interface AuthLayoutProps {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}

/** Acceso en dos columnas: la escena de seguridad a la izquierda, el formulario a la derecha. */
export function AuthLayout({ eyebrow, title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className={styles.marco}>
      <aside className={styles.escena} aria-label="Bandit">
        <Link href="/" className={styles.marca}>
          Bandit
        </Link>

        <div className={styles.mensaje}>
          <p className={styles.eyebrowEscena}>Vigilancia con criterio</p>
          <p className={styles.titular}>Cuida tu local sin perder un detalle.</p>
          <p className={styles.bajadaEscena}>
            Gemini vigila tus cámaras, avisa cuando algo pasa y tú decides si llamar al CAI.
          </p>
          <hr className={styles.divisor} />
          <div className={styles.beneficio}>
            <span className={styles.icono} aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                width="22"
                height="22"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 3 4.5 6v5.5c0 4.6 3.1 8.4 7.5 9.5 4.4-1.1 7.5-4.9 7.5-9.5V6L12 3Z" />
                <path d="m8.8 12.2 2.2 2.2 4.3-4.6" />
              </svg>
            </span>
            <span>
              <strong>IA que describe, no que señala</strong>
              <span className={styles.beneficioTexto}>
                Reconoce situaciones como una pelea o un arma. Nunca identifica personas.
              </span>
            </span>
          </div>
        </div>

        <p className={styles.pie}>
          Bandit · Seguridad para bares y restaurantes · Foto:{" "}
          <a href="https://unsplash.com/photos/LfaN1gswV5c" rel="noreferrer" target="_blank">
            Lianhao Qu en Unsplash
          </a>
        </p>
      </aside>

      <main className={styles.panel} data-tema="archivo">
        <div className={styles.contenido}>
          <Link href="/" className={styles.volver}>
            <span aria-hidden="true">←</span> Volver al inicio
          </Link>
          <p className={styles.eyebrow}>{eyebrow}</p>
          <h1 className={styles.titulo}>{title}</h1>
          <p className={styles.bajada}>{subtitle}</p>
          {children}
        </div>
      </main>
    </div>
  );
}
