"use client";

import Link from "next/link";
import { formatTime } from "@/features/incidents/labels";
import { faceFrameUrl } from "./api";
import styles from "./faces.module.css";
import { comparedFaces, OUTCOME_LABELS } from "./state";
import type { FaceCheck } from "./types";
import { useFaceWatch } from "./useFaceWatch";

function percent(value: number): string {
  return `${Math.round(value * 100)} %`;
}

/** Cada vez que alguien aparece en cámara: con quién se comparó y qué respondió la IA. */
export function FaceWatchPanel({ establishmentId }: { establishmentId: string | undefined }) {
  const watch = useFaceWatch(establishmentId);
  if (!watch) return null;

  return (
    <section className={`vidrio ${styles.seccion}`} aria-labelledby="titulo-rostros">
      <header className={styles.encabezado}>
        <div>
          <h2 id="titulo-rostros">Prueba de rostros</h2>
          <p className={styles.detalle}>
            Cuando alguien aparece en cámara, la IA lo compara solo con las personas de prueba que
            dieron su consentimiento. Sirve para medir si confunde a alguien que no está en la lista.
          </p>
        </div>
        {watch.enabled && (
          <dl className={styles.cifras}>
            <div>
              <dt>Caras comparadas</dt>
              <dd className="cifra">{comparedFaces(watch)}</dd>
            </div>
            <div data-tono="alerta">
              <dt>Coinciden</dt>
              <dd className="cifra">{watch.counts.match}</dd>
            </div>
            <div data-tono="calma">
              <dt>No coinciden</dt>
              <dd className="cifra">{watch.counts.no_match}</dd>
            </div>
            <div>
              <dt>Sin cara</dt>
              <dd className="cifra">{watch.counts.no_face}</dd>
            </div>
            <div>
              <dt>Consultas hoy</dt>
              <dd className="cifra">
                {watch.used} de {watch.limit}
              </dd>
            </div>
          </dl>
        )}
      </header>

      {!watch.enabled ? (
        <p className={styles.detalle}>
          Está apagada. Para encenderla pon <code>FACE_WATCH_ENABLED=true</code> en el archivo{" "}
          <code>.env</code> y reinicia el backend.
        </p>
      ) : watch.people.length === 0 ? (
        <p className={styles.detalle}>
          No hay personas de prueba en la lista. Agrega una con{" "}
          <code>python -m bandit.tools.wanted_match agregar</code>.
        </p>
      ) : (
        <>
          <p className={styles.detalle}>
            Lista de prueba: <strong>{watch.people.join(", ")}</strong>
            {watch.model && <> · modelo {watch.model}</>}
          </p>
          {watch.recent.length === 0 ? (
            <p className={styles.detalle}>
              Esperando a que alguien aparezca o se mueva frente a una cámara en vivo.
            </p>
          ) : (
            <ol className={styles.lista} aria-live="polite" aria-relevant="additions">
              {watch.recent.map((check) => (
                <CheckItem key={check.id} check={check} />
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}

function CheckItem({ check }: { check: FaceCheck }) {
  return (
    <li className={styles.item} data-resultado={check.outcome}>
      {/* eslint-disable-next-line @next/next/no-img-element -- imagen privada en memoria */}
      <img src={faceFrameUrl(check.id)} alt={`Imagen de ${check.camera_name}`} loading="lazy" />
      <div className={styles.texto}>
        <p className={styles.veredicto}>
          <span className={styles.etiqueta}>{OUTCOME_LABELS[check.outcome]}</span>
          {check.person && <strong>{check.person}</strong>}
          {check.outcome !== "error" && <span className="cifra">{percent(check.confidence)}</span>}
        </p>
        <p className={styles.detalle}>
          <time dateTime={check.at}>{formatTime(check.at)}</time> · {check.camera_name}
        </p>
        <p className={styles.explicacion}>{check.explanation}</p>
        {check.alerted && (
          <Link href="/incidentes" className={styles.enlace}>
            Alerta creada en Eventos
          </Link>
        )}
      </div>
    </li>
  );
}
