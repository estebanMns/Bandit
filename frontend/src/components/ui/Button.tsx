import type { ButtonHTMLAttributes } from "react";
import styles from "./Button.module.css";

type Variant = "principal" | "secundario" | "peligro";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "principal", className, type = "button", ...props }: ButtonProps) {
  const classes = [styles.boton, styles[variant], className].filter(Boolean).join(" ");
  return <button type={type} className={classes} {...props} />;
}
