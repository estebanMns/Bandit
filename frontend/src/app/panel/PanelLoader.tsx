"use client";

import dynamic from "next/dynamic";

/** CSR puro: el centro de control muestra video (Workers, canvas, SharedArrayBuffer) y un mapa. */
export const PanelLoader = dynamic(
  () => import("@/features/control/ControlCenter").then((module) => module.ControlCenter),
  { ssr: false },
);
