"use client";

import { useEffect, useMemo, useState } from "react";
import { getActivity } from "@/features/activity/api";
import { connectionOptions } from "@/features/cameras/api";
import { listEstablishments, type Establishment } from "@/features/establishments/api";
import { useLiveEvents } from "@/features/live/useLiveEvents";
import { api } from "@/lib/api";
import { overallStatus, systemStatus, type StatusRow } from "./model";

const LOCAL_KEY = "bandit.local";

export interface Me {
  email: string;
  role: string;
}

export interface ShellData {
  me: Me | null;
  /** null mientras se averigua si hay sesión. */
  signedIn: boolean | null;
  establishments: Establishment[];
  current: Establishment | null;
  rows: StatusRow[];
  overall: { ok: boolean; text: string };
  selectLocal: (id: string) => void;
}

function readLocal(): string | null {
  try {
    return localStorage.getItem(LOCAL_KEY);
  } catch {
    return null;
  }
}

const NOOP = () => undefined;

/**
 * Lo que necesita el marco: usuario, locales y estado del sistema.
 * Nunca redirige: el directorio es público y se ve también sin sesión.
 */
export function useShellData(): ShellData {
  const [me, setMe] = useState<Me | null>(null);
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [establishments, setEstablishments] = useState<Establishment[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [server, setServer] = useState<boolean | null>(null);
  const [imouCloud, setImouCloud] = useState<boolean | null>(null);
  const [model, setModel] = useState<{ enabled: boolean; name: string | null } | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected(readLocal());
    fetch("/api/health")
      .then((response) => setServer(response.ok))
      .catch(() => setServer(false));
    api<Me>("/api/auth/me")
      .then((user) => {
        setMe(user);
        setSignedIn(true);
        listEstablishments()
          .then(setEstablishments)
          .catch(() => setEstablishments([]));
        connectionOptions()
          .then((options) => setImouCloud(options.imou_cloud))
          .catch(() => setImouCloud(false));
      })
      .catch(() => setSignedIn(false));
  }, []);

  const current = useMemo(
    () => establishments.find((item) => item.id === selected) ?? establishments[0] ?? null,
    [establishments, selected],
  );

  useEffect(() => {
    if (!current) return;
    getActivity(current.id)
      .then((snapshot) =>
        setModel({ enabled: snapshot.model_enabled, name: snapshot.model ?? null }),
      )
      .catch(() => setModel(null));
  }, [current]);

  const connection = useLiveEvents(current?.id, NOOP);
  const rows = systemStatus({
    server,
    realtime: connection.connected,
    modelEnabled: model?.enabled ?? null,
    model: model?.name ?? null,
    caiLinked: Boolean(current?.cai_whatsapp),
    imouCloud,
  });

  function selectLocal(id: string) {
    try {
      localStorage.setItem(LOCAL_KEY, id);
    } catch {
      // Sin almacenamiento, el cambio solo dura esta visita.
    }
    // Cada página carga los datos de su local al abrirse: se recarga para que todo coincida.
    window.location.reload();
  }

  return {
    me,
    signedIn,
    establishments,
    current,
    rows,
    overall: overallStatus(rows),
    selectLocal,
  };
}
