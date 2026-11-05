import type { Metadata } from "next";
import Link from "next/link";
import styles from "@/features/landing/landing.module.css";

export const metadata: Metadata = { title: "Guía" };

export default function GuidePage() {
  return (
    <main className={styles.documento}>
      <Link href="/">Volver al inicio</Link>
      <h1>Guía para empezar</h1>
      <ol>
        <li>
          <Link href="/registrarse">Crea tu cuenta</Link> con el nombre y la dirección de tu local.
        </li>
        <li>Pide a la unidad del CAI cercano autorización para escribirles por WhatsApp.</li>
        <li>Guarda ese número en Local y envía un mensaje de prueba.</li>
        <li>Agrega tus cámaras con su dirección RTSP. Se guarda cifrada.</li>
        <li>Abre Monitor durante el turno y deja activas las alertas.</li>
      </ol>
      <h2>Cuando aparezca una alerta</h2>
      <ul>
        <li>Mira el video en vivo antes de decidir.</li>
        <li>Si la situación es real, pulsa Confirmar y avisar al CAI.</li>
        <li>Si fue una falsa alarma, pulsa Descartar.</li>
        <li>Si hay peligro inmediato, llama al 123. WhatsApp no reemplaza esa línea.</li>
      </ul>
      <h2>Directorio</h2>
      <p>
        Es una copia informativa del listado público de la Policía Nacional. Bandit no lo compara
        con tus cámaras. Si crees reconocer a alguien, no intervengas: usa la línea oficial de su
        ficha.
      </p>
    </main>
  );
}
