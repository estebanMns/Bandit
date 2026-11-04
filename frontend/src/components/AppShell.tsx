"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import styles from "./AppShell.module.css";

const LINKS = [
  { href: "/monitor", label: "Monitor" },
  { href: "/incidentes", label: "Incidentes" },
  { href: "/directorio", label: "Directorio" },
  { href: "/ajustes/camaras", label: "Cámaras" },
  { href: "/ajustes/local", label: "Local" },
];

export function AppShell({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className={styles.marco}>
      <header className={styles.cabecera}>
        <Link href="/monitor" className={styles.marca}>
          Bandit
        </Link>
        <nav aria-label="Principal" className={styles.nav}>
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={styles.enlace}
              aria-current={pathname.startsWith(link.href) ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className={styles.lateral}>{aside}</div>
      </header>
      {children}
    </div>
  );
}
