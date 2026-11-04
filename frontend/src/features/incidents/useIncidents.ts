"use client";

import { useCallback, useEffect, useState } from "react";
import { useLiveEvents } from "@/features/live/useLiveEvents";
import type { ServerEvent } from "@/features/live/protocol";
import { listIncidents } from "./api";
import type { Incident } from "./types";

export function upsertIncident(incidents: Incident[], incident: Incident): Incident[] {
  const others = incidents.filter((item) => item.id !== incident.id);
  return [incident, ...others].sort((a, b) => b.detected_at.localeCompare(a.detected_at));
}

export function useIncidents(establishmentId: string | undefined) {
  const [incidents, setIncidents] = useState<Incident[]>([]);

  const reload = useCallback(async () => {
    if (establishmentId) setIncidents(await listIncidents(establishmentId));
  }, [establishmentId]);

  const onEvent = useCallback(
    (event: ServerEvent) => {
      if (event.type === "sync") void reload();
      if (event.type === "incident") {
        setIncidents((current) => upsertIncident(current, event.incident));
      }
    },
    [reload],
  );

  const connection = useLiveEvents(establishmentId, onEvent);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, [reload]);

  const apply = useCallback((incident: Incident) => {
    setIncidents((current) => upsertIncident(current, incident));
  }, []);

  return { incidents, connection, apply };
}
