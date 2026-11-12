import { api } from "@/lib/api";
import { cached, invalidate, peek } from "@/lib/cache";

const KEY = "establishments";

export interface Establishment {
  id: string;
  name: string;
  address: string;
  cai_whatsapp: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

/** Compartido por el marco y la página: una sola petición aunque los dos la pidan a la vez. */
export function listEstablishments(): Promise<Establishment[]> {
  return cached(KEY, () => api<Establishment[]>("/api/establishments"));
}

/** Lo último conocido, para pintar al instante al cambiar de ventana. */
export function knownEstablishments(): Establishment[] | undefined {
  return peek<Establishment[]>(KEY);
}

/** Tras cualquier cambio a un local, la próxima lectura va al servidor. */
async function changed<T>(request: Promise<T>): Promise<T> {
  try {
    return await request;
  } finally {
    invalidate(KEY);
  }
}

export function createEstablishment(name: string, address: string): Promise<Establishment> {
  return changed(
    api("/api/establishments", { method: "POST", body: JSON.stringify({ name, address }) }),
  );
}

export function setCaiWhatsApp(id: string, number: string | null): Promise<Establishment> {
  return changed(
    api(`/api/establishments/${id}/cai-whatsapp`, {
      method: "PUT",
      body: JSON.stringify({ number }),
    }),
  );
}

export function setLocation(id: string, latitude: number, longitude: number): Promise<Establishment> {
  return changed(
    api(`/api/establishments/${id}/location`, {
      method: "PUT",
      body: JSON.stringify({ latitude, longitude }),
    }),
  );
}

export function locateByAddress(id: string): Promise<Establishment> {
  return changed(api(`/api/establishments/${id}/geocode`, { method: "POST" }));
}
