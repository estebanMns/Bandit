"use client";

import { useEffect, useMemo, useState } from "react";
import { getActivity } from "@/features/activity/api";
import { connectionOptions } from "@/features/cameras/api";
import {
  knownEstablishments,
  listEstablishments,
  type Establishment,
} from "@/features/establishments/api";
import { useLiveEvents } from "@/features/live/useLiveEvents";
import { api } from "@/lib/api";
import { cached, invalidate, peek } from "@/lib/cache";
import { overallStatus, systemStatus, type StatusRow } from "./model";

const LOCAL_KEY = "bandit.local";

// Claves de la caché compartida entre ventanas (ver lib/cache.ts).
const ME = "me";
const HEALTH = "health";
const OPTIONS = "connection-options";
const OPTIONS_MAX_AGE_MS = 5 * 60_000;

interface ModelState {
  enabled: boolean;
  name: string | null;
}

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
  // Al cambiar de ventana se arranca con lo ya conocido; en una carga completa la caché está
  // vacía, igual que en el servidor, así que no hay desajuste al hidratar.
  const [known] = useState(() => peek<Me>(ME));
  const [me, setMe] = useState<Me | null>(known ?? null);
  const [signedIn, setSignedIn] = useState<boolean | null>(known ? true : null);
  const [establishments, setEstablishments] = useState<Establishment[]>(() =>
    known ? (knownEstablishments() ?? []) : [],
  );
  const [selected, setSelected] = useState<string | null>(() => (known ? readLocal() : null));
  const [server, setServer] = useState<boolean | null>(() => peek<boolean>(HEALTH) ?? null);
  const [imouCloud, setImouCloud] = useState<boolean | null>(
    () => peek<{ imou_cloud: boolean }>(OPTIONS)?.imou_cloud ?? null,
  );
  const [model, setModel] = useState<ModelState | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected(readLocal());
    cached(HEALTH, () => fetch("/api/health").then((response) => response.ok))
      .then(setServer)
      .catch(() => setServer(false));
    cached(ME, () => api<Me>("/api/auth/me"))
      .then((user) => {
        setMe(user);
        setSignedIn(true);
        listEstablishments()
          .then(setEstablishments)
          .catch(() => setEstablishments([]));
        cached(OPTIONS, connectionOptions, OPTIONS_MAX_AGE_MS)
          .then((options) => setImouCloud(options.imou_cloud))
          .catch(() => setImouCloud(false));
      })
      .catch(() => {
        invalidate(ME);
        setSignedIn(false);
      });
  }, []);

  const current = useMemo(
    () => establishments.find((item) => item.id === selected) ?? establishments[0] ?? null,
    [establishments, selected],
  );

  useEffect(() => {
    if (!current) return;
    const key = `model:${current.id}`;
    const known = peek<ModelState>(key);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (known) setModel(known);
    cached(key, () =>
      getActivity(current.id).then((snapshot) => ({
        enabled: snapshot.model_enabled,
        name: snapshot.model ?? null,
      })),
    )
      .then(setModel)
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
