/** Iniciales para cuando la foto publicada no está disponible: "Jhon Edwin Tenorio" → "JT". */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const first = words.at(0)?.at(0) ?? "";
  const last = words.length > 1 ? (words.at(-1)?.at(0) ?? "") : "";
  return (first + last).toLocaleUpperCase("es-CO") || "?";
}
