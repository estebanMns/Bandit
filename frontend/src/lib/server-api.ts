import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

/** Consulta el backend desde un Server Component, en nombre del usuario. */
export async function serverApi<T>(path: string): Promise<T> {
  const cookieHeader = (await cookies()).toString();
  const response = await fetch(`${BACKEND_URL}${path}`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (response.status === 401) redirect("/ingresar");
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok) throw new Error(`El backend respondió ${response.status}`);
  return (await response.json()) as T;
}
