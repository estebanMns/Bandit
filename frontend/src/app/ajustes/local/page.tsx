"use client";

import { useState, type FormEvent } from "react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { createEstablishment, setCaiWhatsApp } from "@/features/establishments/api";
import { useEstablishment } from "@/features/establishments/useEstablishment";
import { ApiError } from "@/lib/api";
import styles from "../ajustes.module.css";

function message(failure: unknown): string {
  return failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.";
}

export default function LocalPage() {
  const { current, loading, reload } = useEstablishment();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError(null);
    try {
      await createEstablishment(String(data.get("name")), String(data.get("address")));
      await reload();
    } catch (failure) {
      setError(message(failure));
    }
  }

  async function saveNumber(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!current) return;
    const number = String(new FormData(event.currentTarget).get("number")).trim();
    setError(null);
    setSaved(false);
    try {
      await setCaiWhatsApp(current.id, number || null);
      await reload();
      setSaved(true);
    } catch (failure) {
      setError(message(failure));
    }
  }

  return (
    <AppShell>
      <main className={styles.pagina}>
        <h1 className={styles.titulo}>{current?.name ?? "Tu local"}</h1>

        {!loading && !current && (
          <section className={styles.seccion}>
            <h2>Registra tu local</h2>
            <form className={styles.formulario} onSubmit={create}>
              <Field label="Nombre" name="name" required />
              <Field
                label="Dirección"
                name="address"
                hint="Es la dirección que recibirá el CAI en cada alerta."
                required
                error={error}
              />
              <Button type="submit">Registrar local</Button>
            </form>
          </section>
        )}

        {current && (
          <section className={styles.seccion}>
            <p className={styles.ayuda}>{current.address}</p>
            <h2>WhatsApp del CAI más cercano</h2>
            <p className={styles.ayuda}>
              Las alertas que confirmes llegarán a este número. Acuerda su uso con el CAI antes de
              registrarlo.
            </p>
            <form key={current.cai_whatsapp} className={styles.formulario} onSubmit={saveNumber}>
              <Field
                label="Número de WhatsApp"
                name="number"
                type="tel"
                inputMode="tel"
                autoComplete="off"
                placeholder="+57 300 123 4567"
                defaultValue={current.cai_whatsapp ?? ""}
                hint="Incluye el indicativo del país. Déjalo vacío para quitarlo."
                error={error}
              />
              <Button type="submit">Guardar número</Button>
              {saved && (
                <p className={styles.confirmacion} role="status">
                  Número guardado.
                </p>
              )}
            </form>
          </section>
        )}
      </main>
    </AppShell>
  );
}
