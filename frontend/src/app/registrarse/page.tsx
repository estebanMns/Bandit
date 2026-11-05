import type { Metadata } from "next";
import Link from "next/link";
import { RegisterForm } from "./RegisterForm";
import styles from "../ingresar/page.module.css";

export const metadata: Metadata = { title: "Crear cuenta" };

export default function RegisterPage() {
  return (
    <main className={`${styles.pagina} ${styles.registro}`}>
      <h1 className={styles.titulo}>Crea tu cuenta</h1>
      <p className={styles.bajada}>
        Registra tu local y empieza a vigilar el turno. Luego podrás conectar tus cámaras.
      </p>
      <RegisterForm />
      <p className={styles.alterno}>
        ¿Ya tienes cuenta? <Link href="/ingresar">Ingresa aquí</Link>
      </p>
    </main>
  );
}
