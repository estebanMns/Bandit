"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { ControlShell } from "./ControlShell";

/** Título de cada página interna en la cabecera del centro de control. */
const TITLES: [prefix: string, title: string][] = [
  ["/monitor", "Monitor en vivo"],
  ["/incidentes", "Eventos"],
  ["/actividad", "Analítica · actividad de la IA"],
  ["/directorio", "Boletín · los más buscados"],
  ["/ajustes/camaras", "Cámaras"],
  ["/ajustes/local", "Ajustes del local"],
  ["/empezar", "Primeros pasos"],
];

function titleFor(pathname: string): string {
  return TITLES.find(([prefix]) => pathname.startsWith(prefix))?.[1] ?? "Bandit";
}

/** Todas las páginas internas usan el marco del centro de control. */
export function AppShell({
  children,
  aside,
  title,
}: {
  children: ReactNode;
  /** Acciones propias de la página, en la cabecera. */
  aside?: ReactNode;
  title?: string;
}) {
  const pathname = usePathname();
  return (
    <ControlShell title={title ?? titleFor(pathname)} actions={aside}>
      {children}
    </ControlShell>
  );
}
