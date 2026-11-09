"use client";

import dynamic from "next/dynamic";

/** CSR puro: el panel muestra video, que depende de Workers, canvas y SharedArrayBuffer. */
export const PanelLoader = dynamic(
  () => import("./PanelClient").then((module) => module.PanelClient),
  { ssr: false },
);
