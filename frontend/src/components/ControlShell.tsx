"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { LogoutButton } from "@/components/LogoutButton";
import { Icon } from "@/features/control/icons";
import { useShellData } from "@/features/control/useShellData";
import { useClock } from "@/features/control/widgets";
import styles from "./ControlShell.module.css";

const NAV = [
  { href: "/panel", label: "Resumen", icon: "resumen" },
  { href: "/monitor", label: "Monitor", icon: "monitor" },
  { href: "/ajustes/camaras", label: "Cámaras", icon: "camaras" },
  { href: "/incidentes", label: "Eventos", icon: "eventos" },
  { href: "/actividad", label: "Analítica", icon: "analitica" },
  { href: "/directorio", label: "Boletín", icon: "boletin" },
  { href: "/ajustes/local", label: "Ajustes", icon: "ajustes" },
];

const ROLES: Record<string, string> = {
  admin: "Administrador",
  owner: "Dueño",
  operator: "Operador",
};

export const THEME_KEY = "bandit.tema-control";
type Theme = "centinela" | "centinela-claro";

function readTheme(): Theme {
  try {
    return localStorage.getItem(THEME_KEY) === "centinela-claro" ? "centinela-claro" : "centinela";
  } catch {
    return "centinela";
  }
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/panel") return pathname === "/panel";
  return pathname === href || pathname.startsWith(`${href}/`);
}

interface ControlShellProps {
  title: string;
  /** El Panel usa la cabecera como título; las demás páginas traen su propio h1. */
  heading?: boolean;
  /** Acciones propias de la página en la cabecera, junto al reloj. */
  actions?: ReactNode;
  children: ReactNode;
}

/** Marco del centro de control: barra lateral, cabecera y fondo de vidrio líquido. */
export function ControlShell({ title, heading = false, actions, children }: ControlShellProps) {
  const pathname = usePathname();
  const { text: clock } = useClock();
  const shell = useShellData();
  const [theme, setTheme] = useState<Theme>("centinela");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(readTheme());
  }, []);

  function changeTheme(next: Theme) {
    setTheme(next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // Sin almacenamiento el tema solo dura esta visita.
    }
  }

  const initials = (shell.me?.email ?? "?").slice(0, 2).toUpperCase();

  return (
    <div className={styles.raiz} data-tema={theme}>
      <div className={styles.layout}>
        <aside className={`vidrio ${styles.lateral}`} aria-label="Navegación">
          <Link href="/panel" className={styles.logo}>
            <span className={styles.logoIcono}>
              <Icon name="ojo" size={18} />
            </span>
            <span>
              <b>BANDIT</b>
              <small>CENTRO DE CONTROL</small>
            </span>
          </Link>
          <nav className={styles.nav} aria-label="Principal">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive(pathname, item.href) ? "page" : undefined}
              >
                <Icon name={item.icon} />
                {item.label}
              </Link>
            ))}
          </nav>
          <div className={styles.espacio} />
          {shell.signedIn && (
            <section className={`vidrio ${styles.sistema}`} aria-labelledby="titulo-sistema">
              <h2 id="titulo-sistema" className={styles.sistemaTitulo}>
                <span className={styles.punto} data-ok={shell.overall.ok} />
                Estado del sistema
              </h2>
              {shell.rows.map((row) => (
                <div key={row.label} className={styles.sistemaFila}>
                  <span className={styles.tenue}>{row.label}</span>
                  <b data-ok={row.ok}>● {row.value}</b>
                </div>
              ))}
            </section>
          )}
          {shell.signedIn === false ? (
            <Link href="/ingresar" className={`vidrio ${styles.operador} ${styles.ingresar}`}>
              Ingresar
            </Link>
          ) : (
            <div className={`vidrio ${styles.operador}`}>
              <span className={styles.avatar} aria-hidden="true">
                {initials}
              </span>
              <span className={styles.operadorDatos}>
                <strong>{shell.me?.email ?? "…"}</strong>
                <span>{shell.me ? (ROLES[shell.me.role] ?? shell.me.role) : ""}</span>
              </span>
              <LogoutButton />
            </div>
          )}
        </aside>

        <header className={`vidrio ${styles.cabecera}`}>
          {heading ? (
            <h1 className={styles.titulo}>
              {title}
              {shell.signedIn && (
                <span className={styles.estadoGeneral} data-ok={shell.overall.ok}>
                  · {shell.overall.text}
                </span>
              )}
            </h1>
          ) : (
            <p className={styles.titulo}>
              <span className={styles.migas}>Centro de control /</span> {title}
              {shell.signedIn && (
                <span className={styles.estadoGeneral} data-ok={shell.overall.ok}>
                  · {shell.overall.text}
                </span>
              )}
            </p>
          )}
          <div className={styles.herramientas}>
            {actions}
            <div className={styles.tema} role="group" aria-label="Tema">
              <button
                type="button"
                aria-pressed={theme === "centinela-claro"}
                aria-label="Tema claro"
                onClick={() => changeTheme("centinela-claro")}
              >
                ☀
              </button>
              <button
                type="button"
                aria-pressed={theme === "centinela"}
                aria-label="Tema oscuro"
                onClick={() => changeTheme("centinela")}
              >
                ☾
              </button>
            </div>
            {shell.establishments.length > 1 && (
              <select
                className={styles.selector}
                aria-label="Local"
                value={shell.current?.id ?? ""}
                onChange={(event) => shell.selectLocal(event.target.value)}
              >
                {shell.establishments.map((establishment) => (
                  <option key={establishment.id} value={establishment.id}>
                    {establishment.name}
                  </option>
                ))}
              </select>
            )}
            {shell.establishments.length === 1 && shell.current && (
              <span className={styles.selector}>{shell.current.name}</span>
            )}
            <time className={styles.reloj} aria-label="Hora de Colombia">
              {clock}
              <small>COT</small>
            </time>
          </div>
        </header>

        <div className={styles.contenido}>{children}</div>
      </div>
    </div>
  );
}
