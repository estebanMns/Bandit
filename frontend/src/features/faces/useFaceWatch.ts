"use client";

import { useCallback, useEffect, useState } from "react";
import type { ServerEvent } from "@/features/live/protocol";
import { useLiveEvents } from "@/features/live/useLiveEvents";
import { getFaceWatch } from "./api";
import { applyCheck } from "./state";
import type { FaceWatch } from "./types";

/** Estado inicial por HTTP y, después, cada comparación llega en vivo. */
export function useFaceWatch(establishmentId: string | undefined) {
  const [watch, setWatch] = useState<FaceWatch | null>(null);

  const reload = useCallback(async () => {
    if (!establishmentId) return;
    try {
      setWatch(await getFaceWatch(establishmentId));
    } catch {
      setWatch(null);
    }
  }, [establishmentId]);

  const onEvent = useCallback((event: ServerEvent) => {
    if (event.type === "face") {
      setWatch((current) => (current ? applyCheck(current, event.check) : current));
    }
  }, []);

  useLiveEvents(establishmentId, onEvent);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, [reload]);

  return watch;
}
