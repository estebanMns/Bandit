import type { Metadata } from "next";
import Link from "next/link";
import { AuthLayout } from "@/components/AuthLayout";
import { LoginForm } from "./LoginForm";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Ingresar" };

export default function LoginPage() {
  return (
    <AuthLayout
      eyebrow="Acceso seguro"
      title="Bienvenido de nuevo"
      subtitle="Ingresa para ver las cámaras de tu local."
    >
      <LoginForm />
      <p className={styles.separador}>o</p>
      <Link href="/registrarse" className={styles.secundario}>
        Crear una cuenta para tu local <span aria-hidden="true">→</span>
      </Link>
    </AuthLayout>
  );
}
