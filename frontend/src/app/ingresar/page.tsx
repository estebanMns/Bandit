import type { Metadata } from "next";
import { LoginForm } from "./LoginForm";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Ingresar" };

export default function LoginPage() {
  return (
    <main className={styles.pagina}>
      <h1 className={styles.titulo}>Empieza el turno</h1>
      <p className={styles.bajada}>Ingresa con la cuenta que te dio el administrador del local.</p>
      <LoginForm />
    </main>
  );
}
