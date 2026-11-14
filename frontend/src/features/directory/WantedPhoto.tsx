"use client";

import { useState } from "react";
import { initials } from "./initials";
import styles from "./WantedPhoto.module.css";

/** Foto publicada; si no existe en el servidor, las iniciales en vez de un recuadro vacío. */
export function WantedPhoto({
  src,
  name,
  alt = "",
  className,
  lazy = false,
}: {
  src: string | null;
  name: string;
  alt?: string;
  className?: string;
  lazy?: boolean;
}) {
  const [missing, setMissing] = useState(!src);

  if (missing || !src) {
    return (
      <span className={`${className ?? ""} ${styles.iniciales}`} aria-hidden="true">
        {initials(name)}
      </span>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- archivo servido por el backend
    <img
      src={src}
      alt={alt}
      className={className}
      loading={lazy ? "lazy" : undefined}
      onError={() => setMissing(true)}
    />
  );
}
