"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { PasswordField } from "@/components/ui/PasswordField";
import { api, ApiError } from "@/lib/api";
import styles from "../ingresar/page.module.css";

const MIN_PASSWORD_LENGTH = 12;

export function RegisterForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [mismatch, setMismatch] = useState(false);
  const [pending, setPending] = useState(false);

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
      router.push("/monitor");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.");
      setPending(false);
    }
  }

  return (
    <form className={styles.formulario} onSubmit={submit}>
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
