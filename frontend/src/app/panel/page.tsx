import type { Metadata } from "next";
import { PanelLoader } from "./PanelLoader";

export const metadata: Metadata = { title: "Panel" };

export default function PanelPage() {
  return <PanelLoader />;
}
