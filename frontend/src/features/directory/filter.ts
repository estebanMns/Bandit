import type { WantedRecord } from "./types";

export interface DirectoryFilters {
  search: string;
  crime: string;
  region: string;
}

function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

export function filterDirectory(
  records: WantedRecord[],
  { search, crime, region }: DirectoryFilters,
): WantedRecord[] {
  const query = normalize(search.trim());
  return records.filter((record) => {
    const haystack = normalize(`${record.name} ${record.alias ?? ""}`);
    return (
      (!query || haystack.includes(query)) &&
      (!crime || record.crime === crime) &&
      (!region || record.region === region)
    );
  });
}

export function uniqueValues(values: (string | null)[]): string[] {
  const present = values.filter((value): value is string => Boolean(value));
  return [...new Set(present)].sort((a, b) => a.localeCompare(b, "es"));
}
