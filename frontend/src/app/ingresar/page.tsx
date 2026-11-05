import type { Metadata } from "next";
import Link from "next/link";
import { LoginForm } from "./LoginForm";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Ingresar" };

export default function LoginPage() {
  return (
    <main className={styles.pagina}>
      <h1 className={styles.titulo}>Empieza el turno</h1>
      <p className={styles.bajada}>Ingresa con tu cuenta para ver las cámaras de tu local.</p>
      <LoginForm />
      <p className={styles.alterno}>
        ¿Aún no tienes cuenta? <Link href="/registrarse">Crea una cuenta</Link>
      </p>
    </main>
  );
}
