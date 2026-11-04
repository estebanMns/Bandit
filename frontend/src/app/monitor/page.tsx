import type { Metadata } from "next";
import { MonitorLoader } from "./MonitorLoader";

export const metadata: Metadata = { title: "Monitor" };

export default function MonitorPage() {
  return <MonitorLoader />;
}
