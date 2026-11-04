import type { Metadata, Viewport } from "next";
import { Archivo, Atkinson_Hyperlegible_Next } from "next/font/google";
import type { ReactNode } from "react";
import { ServiceWorkerRegistrar } from "@/components/ServiceWorkerRegistrar";
import "@/styles/globals.css";

const archivo = Archivo({
  subsets: ["latin"],
  axes: ["wdth"],
  variable: "--font-archivo",
});

const atkinson = Atkinson_Hyperlegible_Next({
  subsets: ["latin"],
  variable: "--font-atkinson",
});

export const metadata: Metadata = {
  title: { default: "Bandit", template: "%s | Bandit" },
  description: "Cámaras que avisan a tiempo. Tú decides a quién llamar.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = { themeColor: "#101d42" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es-CO" className={`${archivo.variable} ${atkinson.variable}`}>
      <body>
        {children}
        <ServiceWorkerRegistrar />
      </body>
    </html>
  );
}
