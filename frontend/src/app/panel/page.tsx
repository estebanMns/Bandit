import type { Metadata } from "next";
import { PanelLoader } from "./PanelLoader";

export const metadata: Metadata = { title: "Centro de control" };

export default function PanelPage() {
  return <PanelLoader />;
}
