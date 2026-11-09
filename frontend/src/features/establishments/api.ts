import { api } from "@/lib/api";

export interface Establishment {
  id: string;
  name: string;
  address: string;
  cai_whatsapp: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export function listEstablishments(): Promise<Establishment[]> {
  return api("/api/establishments");
}

export function createEstablishment(name: string, address: string): Promise<Establishment> {
  return api("/api/establishments", {
    method: "POST",
    body: JSON.stringify({ name, address }),
  });
}

export function setCaiWhatsApp(id: string, number: string | null): Promise<Establishment> {
  return api(`/api/establishments/${id}/cai-whatsapp`, {
    method: "PUT",
    body: JSON.stringify({ number }),
  });
}

export function setLocation(id: string, latitude: number, longitude: number): Promise<Establishment> {
  return api(`/api/establishments/${id}/location`, {
    method: "PUT",
    body: JSON.stringify({ latitude, longitude }),
  });
}

export function locateByAddress(id: string): Promise<Establishment> {
  return api(`/api/establishments/${id}/geocode`, { method: "POST" });
}
