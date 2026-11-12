import type { ElementType, ReactNode } from "react";
import styles from "./Card.module.css";

interface CardProps {
  title?: ReactNode;
  /** Enlaces o botones a la derecha del título. */
  actions?: ReactNode;
  titleId?: string;
  as?: ElementType;
  className?: string;
  children: ReactNode;
}

/** Tarjeta de vidrio líquido del centro de control: el bloque común de las páginas internas. */
export function Card({
  title,
  actions,
  titleId,
  as: Tag = "section",
  className,
  children,
}: CardProps) {
  return (
    <Tag
      className={["vidrio", styles.tarjeta, className].filter(Boolean).join(" ")}
      aria-labelledby={title && titleId ? titleId : undefined}
    >
      {(title || actions) && (
        <div className={styles.cabecera}>
          {title && <h2 id={titleId}>{title}</h2>}
          {actions && <div className={styles.acciones}>{actions}</div>}
        </div>
      )}
      {children}
    </Tag>
  );
}
