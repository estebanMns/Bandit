"use client";

import { AppShell } from "@/components/AppShell";
import { ActivityDashboard } from "@/features/activity/ActivityDashboard";

/** CSR: datos en vivo de la sesión, nada que prerenderizar. */
export default function ActivityPage() {
  return (
    <AppShell>
      <ActivityDashboard />
    </AppShell>
  );
}
