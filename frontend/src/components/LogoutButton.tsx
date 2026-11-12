"use client";

import { useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";
import { api } from "@/lib/api";
import { clearCache } from "@/lib/cache";
import styles from "./ControlShell.module.css";

function subscribe() {
  return () => undefined;
}

function hasSession() {
  return document.cookie.includes("bandit_csrf=");
}

/** Solo aparece con sesión: el directorio también se puede ver sin cuenta. */
export function LogoutButton() {
  const router = useRouter();
  const visible = useSyncExternalStore(subscribe, hasSession, () => false);
  if (!visible) return null;

  async function logout() {
    await api("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    clearCache();
    router.replace("/ingresar");
  }

  return (
    <button type="button" className={styles.salir} onClick={logout}>
      Salir
    </button>
  );
}
