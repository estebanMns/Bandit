import type { Metadata } from "next";
import Link from "next/link";
import { AuthLayout } from "@/components/AuthLayout";
import styles from "../ingresar/page.module.css";
import { RegisterForm } from "./RegisterForm";

export const metadata: Metadata = { title: "Crear cuenta" };

export default function RegisterPage() {
  return (
    <AuthLayout
      eyebrow="Crear cuenta"
      title="Registra tu local"
      subtitle="Crea tu cuenta y luego conecta tus cámaras."
    >
      <RegisterForm />
      <p className={styles.separador}>o</p>
      <Link href="/ingresar" className={styles.secundario}>
        Ya tengo cuenta, ingresar <span aria-hidden="true">→</span>
      </Link>
    </AuthLayout>
  );
}
