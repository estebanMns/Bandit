"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { PasswordField } from "@/components/ui/PasswordField";
import { ApiError } from "@/lib/api";
import {
  connectDevice,
  createCamera,
  scanNetwork,
  streamUrl,
  type ConnectResult,
  type DiscoveredDevice,
} from "./api";
import styles from "./CameraFinder.module.css";

const OUTCOME_TEXT: Record<ConnectResult["outcome"], string> = {
  connected: "Conectada.",
  wrong_password: "La cámara rechazó el usuario o la clave. Revisa el código de la etiqueta.",
  unreachable:
    "La cámara no responde a este equipo. Algunas cámaras bloquean a un equipo concreto: prueba desde otro computador, con la nube de Imou o con el puente.",
  not_found: "Responde, pero ninguna ruta de video funcionó, ni siquiera las que propuso la IA.",
};

function failure(error: unknown): string {
  return error instanceof ApiError ? error.message : "No hay conexión con el servidor.";
}

interface DeviceRowProps {
  device: DiscoveredDevice;
  establishmentId: string;
  onAdded: () => void;
}

function DeviceRow({ device, establishmentId, onAdded }: DeviceRowProps) {
  const [result, setResult] = useState<ConnectResult | null>(null);
  const [credentials, setCredentials] = useState({ username: "admin", password: "" });
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [added, setAdded] = useState<Set<string>>(new Set());

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const username = String(data.get("username") || "admin");
    const password = String(data.get("password"));
    setCredentials({ username, password });
    setPending(true);
    setMessage(null);
    try {
      setResult(await connectDevice(establishmentId, device.ip, username, password));
    } catch (error) {
      setMessage(failure(error));
    } finally {
      setPending(false);
    }
  }

  async function add(path: string, label: string) {
    setMessage(null);
    try {
      const url = streamUrl(
        device.ip,
        result!.port,
        path,
        credentials.username,
        credentials.password,
      );
      await createCamera(establishmentId, `${device.brand ?? "Cámara"} ${label}`, url);
      setAdded((current) => new Set(current).add(path));
      onAdded();
    } catch (error) {
      setMessage(failure(error));
    }
  }

  return (
    <li className={styles.equipo}>
      <div className={styles.cabecera}>
        <strong>{device.ip}</strong>
        <span className={styles.marca}>
          {device.brand ?? (device.looks_like_camera ? "Cámara" : "Otro equipo")}
        </span>
        <span className={styles.detalle}>Puertos {device.open_ports.join(", ")}</span>
      </div>

      {device.looks_like_camera ? (
        <form className={styles.conectar} onSubmit={connect}>
          <Field label="Usuario" name="username" defaultValue="admin" autoComplete="off" />
          <PasswordField
            label="Clave o código de la etiqueta"
            name="password"
            autoComplete="off"
            required
          />
          <Button type="submit" disabled={pending}>
            {pending ? "Probando rutas…" : "Conectar"}
          </Button>
        </form>
      ) : (
        <p className={styles.detalle}>No ofrece video RTSP: probablemente no es una cámara.</p>
      )}

      {result && (
        <div className={styles.resultado} role="status">
          <p>
            {OUTCOME_TEXT[result.outcome]} Se probaron {result.tried} rutas
            {result.ai_used ? ", incluidas las que sugirió Gemini." : "."}
          </p>
          {result.streams.length > 0 && (
            <ul className={styles.flujos}>
              {result.streams.map((stream) => (
                <li key={stream.path}>
                  <span>
                    {stream.label}
                    {stream.source === "ia" && <span className={styles.ia}> · ruta de la IA</span>}
                  </span>
                  <Button
                    variant="secundario"
                    disabled={added.has(stream.path)}
                    onClick={() => add(stream.path, stream.label)}
                  >
                    {added.has(stream.path) ? "Agregada" : "Agregar"}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {message && (
        <p className={styles.error} role="alert">
          {message}
        </p>
      )}
    </li>
  );
}

interface CameraFinderProps {
  establishmentId: string;
  onAdded: () => void;
}

/** Busca equipos en la red del local y conecta las cámaras con su clave. */
export function CameraFinder({ establishmentId, onAdded }: CameraFinderProps) {
  const [devices, setDevices] = useState<DiscoveredDevice[] | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function scan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const network = String(new FormData(event.currentTarget).get("network"));
    setPending(true);
    setError(null);
    try {
      setDevices(await scanNetwork(establishmentId, network));
    } catch (failed) {
      setError(failure(failed));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={styles.buscador}>
      <form className={styles.red} onSubmit={scan}>
        <Field
          label="Red de tu Wi-Fi"
          name="network"
          defaultValue="192.168.1.0/24"
          hint="Si la IP de tu computador es 192.168.1.108, tu red es 192.168.1.0/24. También puedes escribir la IP de una cámara."
          error={error}
          required
        />
        <Button type="submit" disabled={pending}>
          {pending ? "Buscando… (unos segundos)" : "Buscar cámaras en mi red"}
        </Button>
      </form>

      {devices && devices.length === 0 && (
        <p className={styles.detalle} role="status">
          No se encontró ningún equipo. Revisa la red, o que este computador esté en el mismo Wi-Fi
          que las cámaras.
        </p>
      )}
      {devices && devices.length > 0 && (
        <ul className={styles.lista} aria-label="Equipos encontrados">
          {devices.map((device) => (
            <DeviceRow
              key={device.ip}
              device={device}
              establishmentId={establishmentId}
              onAdded={onAdded}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
