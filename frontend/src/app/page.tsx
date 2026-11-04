import type { Metadata } from "next";
import Link from "next/link";
import { ShiftDemo } from "@/features/landing/ShiftDemo";
import styles from "@/features/landing/landing.module.css";

export const metadata: Metadata = {
  title: { absolute: "Bandit: tus cámaras avisan, tú decides" },
};

const STEPS = [
  {
    title: "La cámara detecta",
    text: "Gemini revisa el movimiento y reconoce situaciones: armas, atracos, peleas, fuego o una persona caída.",
  },
  {
    title: "Tú decides",
    text: "Ves el fotograma y el video en vivo. Si es real, confirmas. Si no, lo descartas y nadie se entera.",
  },
  {
    title: "El CAI recibe el aviso",
    text: "Sale un WhatsApp al número que registraste, con la dirección del local y lo que está pasando.",
  },
];

const LIMITS = [
  "No reconoce rostros ni identifica personas.",
  "No avisa a nadie sin tu confirmación.",
  "No graba de forma continua.",
];

export default function LandingPage() {
  return (
    <div className={styles.portada}>
      <header className={styles.barra}>
        <span className={styles.marca}>Bandit</span>
        <nav aria-label="Principal" className={styles.nav}>
          <Link href="/guia">Guía</Link>
          <Link href="/directorio">Directorio</Link>
          <Link href="/ingresar" className={styles.ingresar}>
            Ingresar
          </Link>
        </nav>
      </header>

      <main>
        <section className={styles.heroe}>
          <h1 className={styles.titular}>
            Tus cámaras avisan.
            <br />
            Tú decides.
          </h1>
          <p className={styles.bajada}>
            Para restaurantes, bares y locales que atienden hasta tarde: Bandit vigila las cámaras
            durante el turno y te muestra lo que merece tu atención.
          </p>
          <ShiftDemo />
        </section>

        <section className={styles.pasos} aria-labelledby="como-funciona">
          <h2 id="como-funciona">Cómo funciona</h2>
          <ol>
            {STEPS.map((step) => (
              <li key={step.title}>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className={styles.limites} aria-labelledby="lo-que-no-hace">
          <h2 id="lo-que-no-hace">Lo que Bandit nunca hace</h2>
          <ul>
            {LIMITS.map((limit) => (
              <li key={limit}>{limit}</li>
            ))}
          </ul>
        </section>
      </main>

      <footer className={styles.pie}>
        <Link href="/privacidad">Privacidad y videovigilancia</Link>
        <span>En una emergencia, llama al 123.</span>
      </footer>
    </div>
  );
}
