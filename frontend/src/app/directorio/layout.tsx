import type { ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import styles from "@/features/directory/directory.module.css";

export default function DirectoryLayout({ children }: { children: ReactNode }) {
  return (
    <AppShell>
      <div className={styles.contenedor}>
        {children}
      </div>
    </AppShell>
  );
}
