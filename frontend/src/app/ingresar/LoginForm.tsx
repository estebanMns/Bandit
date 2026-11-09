"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { PasswordField } from "@/components/ui/PasswordField";
import { api, ApiError } from "@/lib/api";
import styles from "./page.module.css";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    api<{ demo: boolean }>("/api/auth/options")
      .then((options) => setDemo(options.demo))
      .catch(() => setDemo(false));
  }, []);

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
      {demo && (
        <p className={styles.aviso} role="note">
          <strong>Modo de prueba:</strong> usuario <code>admin</code>, clave <code>admin</code>.
        </p>
      )}
      <Field
        label="Correo o usuario"
        name="email"
        autoComplete="username"
        autoCapitalize="none"
        spellCheck={false}
        placeholder="nombre@milocal.com"
        required
      />
      <PasswordField
        label="Clave"
        name="password"
        autoComplete="current-password"
        required
        error={error}
      />
      <Button type="submit" disabled={pending} className={styles.principal}>
        {pending ? "Ingresando" : "Ingresar a Bandit"}
      </Button>
    </form>
  );
}
