import { timingSafeEqual } from "node:crypto";
import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

function isAuthorized(received: string | null): boolean {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret || !received) return false;
  const expected = Buffer.from(secret);
  const candidate = Buffer.from(received);
  return expected.length === candidate.length && timingSafeEqual(expected, candidate);
}

/** Lo llama el backend al terminar una extracción del directorio. */
export async function POST(request: Request) {
  if (!isAuthorized(request.headers.get("x-revalidate"))) {
    return NextResponse.json({ detail: "No autorizado" }, { status: 401 });
  }
  revalidatePath("/directorio", "layout");
  return NextResponse.json({ revalidated: true });
}
