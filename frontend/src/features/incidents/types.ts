export type IncidentStatus =
  | "detected"
  | "confirmed"
  | "discarded"
  | "notified"
  | "notification_failed";

export interface AuditEntry {
  status: IncidentStatus;
  at: string;
  actor: string;
}

export interface Incident {
  id: string;
  establishment_id: string;
  camera_id: string;
  camera_name: string;
  type: string;
  severity: string;
  confidence: number;
  description: string;
  detected_at: string;
  status: IncidentStatus;
  audit: AuditEntry[];
}
