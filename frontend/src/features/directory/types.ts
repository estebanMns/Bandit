export interface WantedRecord {
  slug: string;
  name: string;
  alias: string | null;
  crime: string | null;
  reward: string | null;
  region: string | null;
  hotline_email: string | null;
  hotline_phones: string[];
  photo_url: string | null;
  flyer_url: string | null;
  source_url: string;
  last_seen_at: string | null;
  /** Recompensa en pesos según el texto publicado por la Policía; null si no hay monto. */
  reward_amount: number | null;
  /** Gravedad del delito publicado según una lista fija; null si no se conoce. */
  crime_level: string | null;
}
