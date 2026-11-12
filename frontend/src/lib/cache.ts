/**
 * Caché en memoria de la pestaña para datos que casi no cambian (usuario, locales, opciones).
 * Al cambiar de ventana se muestra al instante lo último conocido y, si ya es viejo, se pide de
 * nuevo. Dos pedidos iguales al mismo tiempo comparten una sola petición.
 * Se vacía al iniciar o cerrar sesión: nunca mezcla datos de dos usuarios.
 */

interface Entry {
  value?: unknown;
  at: number;
  pending?: Promise<unknown>;
}

const entries = new Map<string, Entry>();

export const DEFAULT_MAX_AGE_MS = 30_000;

export function cached<T>(
  key: string,
  load: () => Promise<T>,
  maxAgeMs: number = DEFAULT_MAX_AGE_MS,
): Promise<T> {
  const entry = entries.get(key);
  if (entry?.pending) return entry.pending as Promise<T>;
  if (entry && "value" in entry && Date.now() - entry.at < maxAgeMs) {
    return Promise.resolve(entry.value as T);
  }
  const pending = load().then(
    (value) => {
      entries.set(key, { value, at: Date.now() });
      return value;
    },
    (error: unknown) => {
      const current = entries.get(key);
      if (current?.pending === pending) {
        if (current && "value" in current) entries.set(key, { value: current.value, at: current.at });
        else entries.delete(key);
      }
      throw error;
    },
  );
  entries.set(key, { ...entry, at: entry?.at ?? 0, pending });
  return pending;
}

/** Lo último conocido, aunque sea viejo; undefined si nunca se pidió. */
export function peek<T>(key: string): T | undefined {
  return entries.get(key)?.value as T | undefined;
}

/** Olvida una clave y todas las que empiezan por ella (por ejemplo "establishments"). */
export function invalidate(prefix: string): void {
  for (const key of [...entries.keys()]) {
    if (key === prefix || key.startsWith(`${prefix}:`)) entries.delete(key);
  }
}

export function clearCache(): void {
  entries.clear();
}
