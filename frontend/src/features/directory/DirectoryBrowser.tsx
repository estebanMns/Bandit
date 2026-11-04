"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { filterDirectory, uniqueValues } from "./filter";
import type { WantedRecord } from "./types";
import styles from "./directory.module.css";

export function DirectoryBrowser({ records }: { records: WantedRecord[] }) {
  const [search, setSearch] = useState("");
  const [crime, setCrime] = useState("");
  const [region, setRegion] = useState("");

  const crimes = useMemo(() => uniqueValues(records.map((record) => record.crime)), [records]);
  const regions = useMemo(() => uniqueValues(records.map((record) => record.region)), [records]);
  const visible = filterDirectory(records, { search, crime, region });

  return (
    <>
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
