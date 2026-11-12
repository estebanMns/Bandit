"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./mapa.css";
import { useEffect, useRef, useState } from "react";
import { locateByAddress, setLocation, type Establishment } from "@/features/establishments/api";
import { formatDistance, nearbyCai, PASTO, type NearbyCai } from "@/features/places/api";
import { ApiError } from "@/lib/api";
import styles from "./control.module.css";

const NARINO = L.latLngBounds([0, -79.5], [3, -76.5]);

function marker(kind: "local" | "cai") {
  return L.divIcon({
    className: `bandit-marcador bandit-marcador-${kind}`,
    iconSize: kind === "local" ? [18, 18] : [14, 14],
  });
}

interface CaiMapProps {
  establishment: Establishment;
  onLocated: () => Promise<void> | void;
}

/** Mapa de Pasto con el local y los CAI cercanos, según OpenStreetMap. */
export function CaiMap({ establishment, onLocated }: CaiMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);
  const [nearby, setNearby] = useState<NearbyCai | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [placing, setPlacing] = useState(false);
  const located = establishment.latitude != null && establishment.longitude != null;
  const center: [number, number] = located
    ? [establishment.latitude!, establishment.longitude!]
    : PASTO;

  useEffect(() => {
    if (!container.current || map.current) return;
    const instance = L.map(container.current, {
      maxBounds: NARINO,
      minZoom: 10,
      maxZoom: 18,
    }).setView(PASTO, 14);
    L.tileLayer("/api/map/tiles/{z}/{x}/{y}.png", {
      minZoom: 10,
      maxZoom: 18,
      attribution: "© colaboradores de OpenStreetMap",
    }).addTo(instance);
    layer.current = L.layerGroup().addTo(instance);
    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!located) return;
    nearbyCai(center[0], center[1])
      .then(setNearby)
      .catch(() => setMessage("No se pudieron consultar los CAI cercanos en este momento."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [located, center[0], center[1]]);

  useEffect(() => {
    const instance = map.current;
    const group = layer.current;
    if (!instance || !group) return;
    group.clearLayers();
    if (located) {
      L.marker(center, { icon: marker("local"), title: establishment.name })
        .bindTooltip(establishment.name)
        .addTo(group);
    }
    for (const place of located ? (nearby?.places ?? []) : []) {
      L.marker([place.latitude, place.longitude], { icon: marker("cai"), title: place.name })
        .bindTooltip(`${place.name} · ${formatDistance(place.distance_m)}`)
        .addTo(group);
    }
    instance.setView(center, located ? 15 : 14);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nearby, located, center[0], center[1], establishment.name]);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !placing) return;
    const pick = (event: L.LeafletMouseEvent) => {
      setPlacing(false);
      void save(() => setLocation(establishment.id, event.latlng.lat, event.latlng.lng));
    };
    instance.once("click", pick);
    return () => {
      instance.off("click", pick);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [placing]);

  async function save(action: () => Promise<unknown>) {
    setMessage(null);
    try {
      await action();
      await onLocated();
    } catch (failure) {
      setMessage(
        failure instanceof ApiError ? failure.message : "No hay conexión con el servidor.",
      );
    }
  }

  function locateWithGps() {
    if (!navigator.geolocation) {
      setMessage("Este navegador no permite conocer la ubicación.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        void save(() =>
          setLocation(establishment.id, position.coords.latitude, position.coords.longitude),
        ),
      () => setMessage("No se pudo obtener tu ubicación. Revisa el permiso del navegador."),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  }

  const nearest = located ? (nearby?.places.slice(0, 3) ?? []) : [];

  return (
    <section className={`vidrio ${styles.panel}`} aria-labelledby="titulo-mapa">
      <div className={styles.panelCabecera}>
        <h2 id="titulo-mapa">Mapa · Pasto y CAI cercanos</h2>
        <span className={styles.tenue}>{located ? establishment.name : "Local sin ubicar"}</span>
      </div>
      <div className={styles.mapa}>
        <div
          ref={container}
          className={styles.mapaLienzo}
          role="application"
          aria-label="Mapa de Pasto con el local y los CAI cercanos"
        />
      </div>
      <div className={styles.mapaAcciones}>
        <button type="button" className={styles.boton} onClick={locateWithGps}>
          Usar mi ubicación actual
        </button>
        <button
          type="button"
          className={styles.boton}
          onClick={() => void save(() => locateByAddress(establishment.id))}
        >
          Ubicar por la dirección
        </button>
        <button
          type="button"
          className={styles.boton}
          aria-pressed={placing}
          onClick={() => setPlacing((value) => !value)}
        >
          {placing ? "Toca el mapa…" : "Marcar en el mapa"}
        </button>
      </div>
      {message && (
        <p role="alert" style={{ color: "var(--error)", fontSize: 12.5 }}>
          {message}
        </p>
      )}
      {located && (
        <>
          {nearest.length > 0 ? (
            <ol className={styles.cais} aria-label="CAI más cercanos">
              {nearest.map((place) => (
                <li key={`${place.name}-${place.latitude}`}>
                  <span>{place.name}</span>
                  <span className={styles.cifra}>{formatDistance(place.distance_m)}</span>
                </li>
              ))}
            </ol>
          ) : (
            nearby && (
              <p className={styles.tenue}>
                OpenStreetMap no tiene CAI registrados a menos de 5 km de este punto.
              </p>
            )
          )}
          <p className={styles.fuente}>
            CAI según {nearby?.source ?? "OpenStreetMap"}. Puede haber CAI sin registrar.
          </p>
        </>
      )}
    </section>
  );
}
