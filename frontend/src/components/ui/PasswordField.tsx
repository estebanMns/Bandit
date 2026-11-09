"use client";

import { useId, useState, type InputHTMLAttributes } from "react";
import styles from "./Field.module.css";
import own from "./PasswordField.module.css";

interface PasswordFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
  hint?: string;
  error?: string | null;
}

/** Campo de clave con botón para verla antes de enviar. */
export function PasswordField({ label, hint, error, ...input }: PasswordFieldProps) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  const hintId = `${id}-ayuda`;
  const errorId = `${id}-error`;
  const describedBy = [hint && hintId, error && errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={styles.campo}>
      <label htmlFor={id} className={styles.etiqueta}>
        {label}
      </label>
      <div className={own.contenedor}>
        <input
          id={id}
          type={visible ? "text" : "password"}
          className={`${styles.entrada} ${own.entrada}`}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          {...input}
        />
        <button
          type="button"
          className={own.mostrar}
          aria-controls={id}
          onClick={() => setVisible((current) => !current)}
        >
          {visible ? "Ocultar" : "Mostrar"}
        </button>
      </div>
      {hint && (
        <p id={hintId} className={styles.ayuda}>
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
