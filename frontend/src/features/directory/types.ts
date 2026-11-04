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
}
