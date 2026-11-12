"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { knownEstablishments, listEstablishments, type Establishment } from "./api";

const STORAGE_KEY = "bandit.local";

interface EstablishmentState {
  establishments: Establishment[];
  current: Establishment | null;
  loading: boolean;
  select: (id: string) => void;
  reload: () => Promise<void>;
}

function readSelected(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

/**
 * Local activo del usuario. Envía a ingresar si la sesión ya no es válida.
 * Al cambiar de ventana arranca con los locales ya conocidos: no hay espera ni pantalla vacía.
 */
export function useEstablishment(): EstablishmentState {
  const router = useRouter();
  // En una carga completa la caché está vacía, igual que en el servidor: no hay desajuste.
  const [known] = useState(knownEstablishments);
  const [establishments, setEstablishments] = useState<Establishment[]>(known ?? []);
  const [selectedId, setSelectedId] = useState<string | null>(() => (known ? readSelected() : null));
  const [loading, setLoading] = useState(!known);

  const reload = useCallback(async () => {
    try {
      const loaded = await listEstablishments();
      setEstablishments(loaded);
      setSelectedId(readSelected());
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) router.replace("/ingresar");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, [reload]);

  const select = useCallback((id: string) => {
    localStorage.setItem(STORAGE_KEY, id);
    setSelectedId(id);
  }, []);

  const current =
    establishments.find((establishment) => establishment.id === selectedId) ??
    establishments[0] ??
    null;

  return { establishments, current, loading, select, reload };
}
