import type { Metadata } from "next";
import Link from "next/link";
import styles from "@/features/landing/landing.module.css";

export const metadata: Metadata = { title: "Privacidad y videovigilancia" };

export default function PrivacyPage() {
  return (
    <main className={styles.documento}>
      <Link href="/">Volver al inicio</Link>
      <h1>Privacidad y videovigilancia</h1>
      <p>
        Esta página resume cómo funciona Bandit. Cada local es responsable de avisar a sus clientes
        que hay cámaras y de adaptar este texto a su política de datos, con asesoría legal, según
        la Ley 1581 de 2012.
      </p>
      <h2>Qué se procesa</h2>
      <ul>
        <li>Fotogramas con movimiento, enviados a Google Gemini para clasificar la situación.</li>
        <li>El fotograma de cada incidente, guardado como evidencia durante 7 días.</li>
        <li>El registro de quién confirmó o descartó cada incidente.</li>
      </ul>
      <h2>Qué no se hace</h2>
      <ul>
        <li>No se reconoce ni identifica a las personas por su rostro.</li>
        <li>No se crean plantillas ni vectores biométricos.</li>
        <li>No se compara el video con el directorio de los más buscados.</li>
        <li>No se graba video de forma continua.</li>
      </ul>
      <h2>Aviso sugerido para el local</h2>
      <p>
        Este establecimiento cuenta con videovigilancia con fines de seguridad. Un sistema
        automático ayuda a detectar situaciones de riesgo y una persona revisa cada alerta.
      </p>
      <h2>Directorio</h2>
      <p>
        Contiene datos publicados por la Policía Nacional, con su fuente y fecha. Un registro se
        retira cuando deja de aparecer en el listado oficial.
      </p>
    </main>
  );
}
