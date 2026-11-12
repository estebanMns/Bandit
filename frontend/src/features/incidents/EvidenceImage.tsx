"use client";

import { useState } from "react";

/**
 * Fotograma de un incidente. La evidencia se borra al vencer su retención (o no existe en este
 * equipo): entonces se explica en vez de mostrar una imagen rota.
 */
export function EvidenceImage({
  incidentId,
  alt,
  className,
}: {
  incidentId: string;
  alt: string;
  className?: string;
}) {
  const [missing, setMissing] = useState(false);

  if (missing) {
    return (
      <p className={className} role="note" data-sin-evidencia="true">
        La evidencia de este evento ya no está disponible.
      </p>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- imagen privada, sin optimizar
    <img
      className={className}
      src={`/api/incidents/${incidentId}/evidence`}
      alt={alt}
      onError={() => setMissing(true)}
    />
  );
}
