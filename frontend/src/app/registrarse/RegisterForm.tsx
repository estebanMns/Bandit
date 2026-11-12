"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { PasswordField } from "@/components/ui/PasswordField";
import { LOGIN_AFTER_SIGNUP, REGISTERED_EMAIL_KEY } from "@/features/onboarding/signup";
import { api, ApiError } from "@/lib/api";
import styles from "../ingresar/page.module.css";

const MIN_PASSWORD_LENGTH = 12;
const REDIRECT_MS = 2500;

export function RegisterForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [mismatch, setMismatch] = useState(false);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!done) return;
    const timer = window.setTimeout(() => router.replace(LOGIN_AFTER_SIGNUP), REDIRECT_MS);
    return () => window.clearTimeout(timer);
  }, [done, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError(null);

    const password = String(data.get("password"));
    const matches = password === data.get("confirmation");
    setMismatch(!matches);
    if (!matches) return;

    setPending(true);
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: data.get("email"),
          password,
          local_name: data.get("localName"),
          local_address: data.get("localAddress"),
        }),
      });
      sessionStorage.setItem(REGISTERED_EMAIL_KEY, String(data.get("email")));
      setDone(true);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
      setPending(false);
    }
  }

  if (done) {
    return (
      <div className={styles.exito} role="status">
        <span className={styles.exitoIcono} aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="26"
            height="26"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <path d="m5 12.5 4.5 4.5L19 7" />
          </svg>
        </span>
        <div>
          <p className={styles.exitoTitulo}>Registro exitoso</p>
          <p>Tu cuenta y tu local quedaron creados. Ahora ingresa con tu correo y clave.</p>
          <p className={styles.exitoNota}>Te llevamos al ingreso en unos segundos…</p>
        </div>
        <Link href={LOGIN_AFTER_SIGNUP} className={styles.exitoBoton}>
          Ir a ingresar
        </Link>
      </div>
    );
  }

  return (
    // method="post": si el JavaScript no carga, la clave nunca queda en la dirección.
    <form className={styles.formulario} method="post" onSubmit={submit}>
      <fieldset className={styles.grupo}>
        <legend>Tu local</legend>
        <Field label="Nombre del local" name="localName" autoComplete="organization" required />
        <Field
          label="Dirección"
          name="localAddress"
          autoComplete="street-address"
          hint="Es la dirección que recibirá el CAI en cada alerta."
          required
        />
      </fieldset>
      <fieldset className={styles.grupo}>
        <legend>Tu cuenta</legend>
        <Field label="Correo" name="email" type="email" autoComplete="username" required />
        <PasswordField
          label="Clave"
          name="password"
          autoComplete="new-password"
          minLength={MIN_PASSWORD_LENGTH}
          hint={`Mínimo ${MIN_PASSWORD_LENGTH} caracteres.`}
          required
        />
        <PasswordField
          label="Repite la clave"
          name="confirmation"
          autoComplete="new-password"
          required
          error={mismatch ? "Las claves no coinciden." : error}
        />
      </fieldset>
      <Button type="submit" disabled={pending} className={styles.principal}>
        {pending ? "Creando cuenta" : "Crear cuenta"}
      </Button>
    </form>
  );
}
