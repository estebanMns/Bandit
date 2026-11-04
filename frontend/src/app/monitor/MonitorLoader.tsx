"use client";

import dynamic from "next/dynamic";

/** CSR puro: el monitor depende de Workers, canvas y SharedArrayBuffer. */
export const MonitorLoader = dynamic(
  () => import("./MonitorClient").then((module) => module.MonitorClient),
  { ssr: false },
);
