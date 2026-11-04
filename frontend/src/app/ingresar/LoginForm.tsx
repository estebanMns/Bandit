"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { api, ApiError } from "@/lib/api";
import styles from "./page.module.css";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
      });
      router.push("/monitor");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
      setPending(false);
    }
  }

  return (
    <form className={styles.formulario} onSubmit={submit}>
      <Field label="Correo" name="email" type="email" autoComplete="username" required />
      <Field
        label="Clave"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        error={error}
      />
      <Button type="submit" disabled={pending}>
        {pending ? "Ingresando" : "Ingresar"}
      </Button>
    </form>
  );
}
