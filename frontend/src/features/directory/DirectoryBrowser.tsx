"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { filterDirectory, uniqueValues } from "./filter";
import { formatReward, priorityRecords } from "./priority";
import type { WantedRecord } from "./types";
import styles from "./directory.module.css";

export function DirectoryBrowser({ records }: { records: WantedRecord[] }) {
  const [search, setSearch] = useState("");
  const [crime, setCrime] = useState("");
  const [region, setRegion] = useState("");

  const crimes = useMemo(() => uniqueValues(records.map((record) => record.crime)), [records]);
  const regions = useMemo(() => uniqueValues(records.map((record) => record.region)), [records]);
  const visible = filterDirectory(records, { search, crime, region });
  const filtering = Boolean(search || crime || region);
  const priority = priorityRecords(records);

  return (
    <>
      {!filtering && priority.length > 0 && (
        <section className={styles.prioridad} aria-labelledby="titulo-prioridad">
          <h2 id="titulo-prioridad">Prioridad</h2>
          <p className={styles.tenue}>
            Ordenado por la recompensa que ofrece la Policía y, después, por la gravedad del delito
            publicado. Bandit no califica a las personas: solo ordena lo que la Policía publicó.
          </p>
          <ol className={styles.prioritarios}>
            {priority.map((record, index) => (
              <li key={record.slug}>
                <Link href={`/directorio/${record.slug}`} className={styles.prioritario}>
                  <span className={styles.puesto}>{index + 1}</span>
                  {record.photo_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={record.photo_url} alt="" className={styles.fotoPrioridad} />
                  )}
                  <span className={styles.nombre}>{record.name}</span>
                  <span className={styles.recompensa}>{formatReward(record)}</span>
                  {(record.crime_level ?? record.crime) && (
                    <span className={styles.tenue}>{record.crime ?? record.crime_level}</span>
                  )}
                </Link>
              </li>
            ))}
          </ol>
        </section>
      )}

      <form className={styles.filtros} role="search" onSubmit={(event) => event.preventDefault()}>
        <label>
          Nombre o alias
          <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        <label>
          Delito
          <select value={crime} onChange={(event) => setCrime(event.target.value)}>
            <option value="">Todos</option>
            {crimes.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Región
          <select value={region} onChange={(event) => setRegion(event.target.value)}>
            <option value="">Todas</option>
            {regions.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
      </form>

      <p role="status" className={styles.conteo}>
        {visible.length === 1 ? "1 registro" : `${visible.length} registros`}
      </p>

      {visible.length === 0 ? (
        <p>Ningún registro coincide. Prueba con otro nombre o quita un filtro.</p>
      ) : (
        <ul className={styles.archivo}>
          {visible.map((record) => (
            <li key={record.slug}>
              <Link href={`/directorio/${record.slug}`} className={styles.ficha}>
                {record.photo_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={record.photo_url} alt="" loading="lazy" className={styles.foto} />
                )}
                <span className={styles.nombre}>{record.name}</span>
                {record.alias && <span>Alias {record.alias}</span>}
                {record.crime && <span className={styles.tenue}>{record.crime}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
