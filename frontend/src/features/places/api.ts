import { api } from "@/lib/api";

export interface Place {
  name: string;
  latitude: number;
  longitude: number;
  distance_m: number;
}

export interface NearbyCai {
  source: string;
  places: Place[];
}

/** Centro de Pasto: donde abre el mapa si el local todavía no tiene ubicación. */
export const PASTO: [number, number] = [1.2136, -77.2811];

export function nearbyCai(latitude: number, longitude: number, radius = 5000): Promise<NearbyCai> {
  const query = new URLSearchParams({
    lat: String(latitude),
    lng: String(longitude),
    radius: String(radius),
  });
  return api(`/api/places/nearby-cai?${query}`);
}

export function formatDistance(meters: number): string {
  return meters < 1000 ? `${meters} m` : `${(meters / 1000).toFixed(1).replace(".", ",")} km`;
}
