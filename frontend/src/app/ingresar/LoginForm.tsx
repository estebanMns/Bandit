"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { PasswordField } from "@/components/ui/PasswordField";
import { REGISTERED_EMAIL_KEY } from "@/features/onboarding/signup";
import { api, ApiError } from "@/lib/api";
import styles from "./page.module.css";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [demo, setDemo] = useState(false);
  const [justRegistered, setJustRegistered] = useState(false);
  const [email, setEmail] = useState("");

  useEffect(() => {
    // Se lee en el cliente para que /ingresar siga siendo una página estática.
    if (new URLSearchParams(window.location.search).get("registro") !== "exitoso") return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setJustRegistered(true);
    setEmail(sessionStorage.getItem(REGISTERED_EMAIL_KEY) ?? "");
    sessionStorage.removeItem(REGISTERED_EMAIL_KEY);
  }, []);

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
      router.push("/panel");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
      setPending(false);
    }
  }

  return (
    <form className={styles.formulario} onSubmit={submit}>
      {justRegistered && (
        <p className={styles.exitoAviso} role="status">
          <strong>Cuenta creada.</strong> Ingresa para empezar a configurar tu local.
        </p>
      )}
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
        value={email}
        onChange={(event) => setEmail(event.target.value)}
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
