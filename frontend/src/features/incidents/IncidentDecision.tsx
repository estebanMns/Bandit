"use client";

import { useRouter } from "next/navigation";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { DecisionActions } from "./DecisionActions";
import type { Incident } from "./types";

/** Decisión desde Eventos: al aceptar o rechazar se recarga el estado y el registro. */
export function IncidentDecision({ incident }: { incident: Incident }) {
  const router = useRouter();
  const { establishments, loading } = useEstablishment();
  if (loading) return null;
  const local = establishments.find((item) => item.id === incident.establishment_id);

  return (
    <DecisionActions
      incident={incident}
      caiNumber={local?.cai_whatsapp ?? null}
      onChange={() => router.refresh()}
    />
  );
}
