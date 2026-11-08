"use client";

import { useCallback, useEffect, useState } from "react";
import type { ServerEvent } from "@/features/live/protocol";
import { useLiveEvents } from "@/features/live/useLiveEvents";
import { getActivity } from "./api";
import { applyEntry } from "./state";
import type { ActivitySnapshot } from "./types";

/** Foto inicial por HTTP y, después, cada muestreo llega en vivo por el SharedWorker. */
export function useActivity(establishmentId: string | undefined) {
  const [snapshot, setSnapshot] = useState<ActivitySnapshot | null>(null);
  const [error, setError] = useState(false);

  const reload = useCallback(async () => {
    if (!establishmentId) return;
    try {
      setSnapshot(await getActivity(establishmentId));
      setError(false);
    } catch {
      setError(true);
    }
  }, [establishmentId]);

  const onEvent = useCallback(
    (event: ServerEvent) => {
      if (event.type === "sync") void reload();
      if (event.type === "analysis") {
        setSnapshot((current) => (current ? applyEntry(current, event.cameraName, event.entry) : current));
      }
    },
    [reload],
  );

  const connection = useLiveEvents(establishmentId, onEvent);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, [reload]);

  return { snapshot, error, connection };
}
