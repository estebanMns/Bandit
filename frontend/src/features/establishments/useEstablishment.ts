"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { listEstablishments, type Establishment } from "./api";

const STORAGE_KEY = "bandit.local";

interface EstablishmentState {
  establishments: Establishment[];
  current: Establishment | null;
  loading: boolean;
  select: (id: string) => void;
  reload: () => Promise<void>;
}

/** Local activo del usuario. Envía a ingresar si la sesión ya no es válida. */
export function useEstablishment(): EstablishmentState {
  const router = useRouter();
  const [establishments, setEstablishments] = useState<Establishment[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      const loaded = await listEstablishments();
      setEstablishments(loaded);
      setSelectedId(localStorage.getItem(STORAGE_KEY));
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
