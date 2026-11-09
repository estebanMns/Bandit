import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { ShiftDemo } from "@/features/landing/ShiftDemo";
import styles from "@/features/landing/portada.module.css";

export const metadata: Metadata = {
  title: { absolute: "Bandit: tus cámaras avisan, tú decides" },
};

/** Cifras fijas y verdaderas: describen cómo funciona Bandit, no métricas inventadas. */
const FACTS = [
  {
    label: "Situaciones que reconoce",
    value: "5",
    note: "Armas, atracos, peleas, fuego y emergencias de salud.",
    tone: styles.cifraSodio,
  },
  {
    label: "Detecciones seguidas",
    value: "2",
    note: "Antes de alertar, para evitar falsas alarmas.",
    tone: styles.cifraNoche,
  },
  {
    label: "Rostros identificados",
    value: "0",
    note: "Describe situaciones, nunca señala personas.",
    tone: styles.cifraBaliza,
  },
  {
    label: "Confirmación tuya",
    value: "1",
    note: "Nadie avisa al CAI sin que tú lo decidas.",
    tone: styles.cifraAgua,
  },
];

const ICONS: Record<string, ReactNode> = {
  camara: <path d="M3 7.5 15 4l1.5 5L4.5 12.5 3 7.5Zm9.7 3.4L14 15h4m-14-2.5V20" />,
  decision: <path d="m5 12.5 4.5 4.5L19 7" />,
  aviso: <path d="M4 12.5 20 5l-4 15-4.5-5.5L4 12.5Zm7.5 2L20 5" />,
};

const STEPS = [
  {
    icon: "camara",
    title: "La cámara detecta",
    text: "Gemini revisa el movimiento y reconoce situaciones: armas, atracos, peleas, fuego o una persona caída.",
  },
  {
    icon: "decision",
    title: "Tú decides",
    text: "Ves el fotograma y el video en vivo. Si es real, confirmas. Si no, lo descartas y nadie se entera.",
  },
  {
    icon: "aviso",
    title: "El CAI recibe el aviso",
    text: "Sale un WhatsApp al número que registraste, con la dirección del local y lo que está pasando.",
  },
];

const LIMITS = [
  "No reconoce rostros ni identifica personas.",
  "No avisa a nadie sin tu confirmación.",
  "No graba de forma continua.",
];

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export default function LandingPage() {
  return (
    <div className={styles.portada} data-tema="archivo">
      <header className={`${styles.contenedor} ${styles.barra}`}>
        <Link href="/" className={styles.marca}>
          <span className={styles.marcaIcono} aria-hidden="true">
            <Icon>
              <circle cx="12" cy="12" r="3.2" />
              <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
            </Icon>
          </span>
          Bandit
        </Link>
        <nav aria-label="Principal" className={styles.nav}>
          <a href="#como-funciona">Cómo funciona</a>
          <Link href="/guia">Guía</Link>
          <Link href="/directorio">Directorio</Link>
        </nav>
        <Link href="/ingresar" className={styles.ingresar}>
          Ingresar
        </Link>
      </header>

      <main className={styles.contenedor}>
        <section className={styles.heroe} aria-labelledby="titular">
          <div className={styles.heroeContenido}>
            <p className={styles.eyebrow}>Vigilancia con IA para bares y restaurantes</p>
            <h1 id="titular" className={styles.titular}>
              Tus cámaras avisan.
              <br />
              Tú decides.
            </h1>
            <p className={styles.bajada}>
              Bandit vigila tus cámaras durante el turno, reconoce cuándo algo pasa y te deja
              decidir si avisar al CAI más cercano.
            </p>
            <div className={styles.acciones}>
              <Link href="/registrarse" className={styles.botonPrincipal}>
                Crear cuenta
              </Link>
              <Link href="/ingresar" className={styles.botonContorno}>
                Ya tengo cuenta
              </Link>
            </div>
          </div>

          <Link href="/guia" className={styles.masInfo}>
            <span className={styles.masInfoCabecera}>
              <span>Más información</span>
              <span aria-hidden="true">→</span>
            </span>
            <span className={styles.masInfoCuerpo}>
              <span className={styles.miniaturas}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/portada/fachada.webp" alt="" />
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/portada/poste.webp" alt="" />
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/portada/domo.webp" alt="" />
              </span>
              <span>
                <span className={styles.masInfoTitulo}>Conecta tus cámaras</span>
                <span className={styles.masInfoTexto}>
                  Guía paso a paso: RTSP, nube de Imou o un puente en tu red.
                </span>
              </span>
            </span>
          </Link>
        </section>

        <dl className={styles.cifras} aria-label="Cómo trabaja Bandit en cifras">
          {FACTS.map((fact) => (
            <div key={fact.label} className={`${styles.cifra} ${fact.tone}`}>
              <dt>{fact.label}</dt>
              <dd>
                <span className={styles.cifraValor}>{fact.value}</span>
                <span className={styles.cifraNota}>{fact.note}</span>
              </dd>
            </div>
          ))}
        </dl>

        <section className={styles.seccion} aria-labelledby="como-funciona">
          <h2 id="como-funciona">Cómo funciona</h2>
          <ol className={styles.pasos}>
            {STEPS.map((step, index) => (
              <li key={step.title} className={styles.paso}>
                <span className={styles.pasoIcono}>
                  <Icon>{ICONS[step.icon]}</Icon>
                </span>
                <span className={styles.pasoNumero}>Paso {index + 1}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className={styles.seccion} aria-labelledby="un-turno">
          <div className={styles.demo} data-tema="noche">
            <h2 id="un-turno">Así se ve un turno</h2>
            <ShiftDemo />
          </div>
        </section>

        <section className={styles.seccion} aria-labelledby="lo-que-no-hace">
          <h2 id="lo-que-no-hace">Lo que Bandit nunca hace</h2>
          <ul className={styles.limites}>
            {LIMITS.map((limit) => (
              <li key={limit}>
                <Icon>
                  <path d="M6 6l12 12M18 6 6 18" />
                </Icon>
                {limit}
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className={`${styles.contenedor} ${styles.pie}`}>
        <span>
          <Link href="/privacidad">Privacidad y videovigilancia</Link> ·{" "}
          <Link href="/directorio">Directorio de los más buscados</Link>
        </span>
        <span>En una emergencia, llama al 123.</span>
        <span>
          Fotos de Alex Knight, Miłosz Klinowski, Milan Malkomes y Jakub Żerdzicki en{" "}
          <a href="https://unsplash.com/license" rel="noreferrer" target="_blank">
            Unsplash
          </a>
          .
        </span>
      </footer>
    </div>
  );
}
