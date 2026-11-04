import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/**
 * Flujo real contra `docker compose up`. Requiere:
 *   E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD y E2E_RTSP_URL.
 * Con E2E_SHOTS=carpeta guarda capturas de cada pantalla.
 */

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "";
const RTSP_URL = process.env.E2E_RTSP_URL ?? "";
const SHOTS = process.env.E2E_SHOTS;
const DIRECTORY_SAMPLE = process.env.E2E_DIRECTORY_SAMPLE;
const MOBILE = { width: 390, height: 844 };

async function shot(page: Page, name: string, fullPage = true) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage });
}

async function login(page: Page) {
  await page.goto("/ingresar");
  await page.getByLabel("Correo").fill(ADMIN_EMAIL);
  await page.getByLabel("Clave").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await page.waitForURL("**/monitor");
}

/** Devuelve cuántos píxeles distintos hay en una muestra del lienzo. */
function distinctPixels(page: Page): Promise<number> {
  return page.evaluate(() => {
    const canvas = document.querySelector("canvas");
    if (!canvas || canvas.width < 2) return 0;
    const context = canvas.getContext("2d");
    const data = context?.getImageData(0, 0, canvas.width, canvas.height).data;
    const seen = new Set<number>();
    for (let index = 0; data && index < data.length; index += 4004) {
      seen.add(data[index]! * 65536 + data[index + 1]! * 256 + data[index + 2]!);
    }
    return seen.size;
  });
}

async function expectAccessible(page: Page, label: string) {
  const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const summary = violations.map(
    (item) => `${label}: ${item.id} (${item.nodes.length}) ${item.nodes[0]?.target}`,
  );
  expect(summary).toEqual([]);
}

test("las pantallas cumplen WCAG 2 AA", async ({ page }) => {
  for (const path of ["/", "/guia", "/privacidad", "/ingresar", "/directorio"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await expectAccessible(page, path);
  }
  await login(page);
  for (const path of ["/monitor", "/incidentes", "/ajustes/camaras", "/ajustes/local"]) {
    await page.goto(path);
    // El video mantiene la red ocupada: se espera a que la pantalla cargue sus datos.
    await page.waitForTimeout(1_500);
    await expectAccessible(page, path);
  }
});

test("portada y páginas públicas", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Tus cámaras avisan");
  await shot(page, "portada-escritorio");
  await page.setViewportSize(MOBILE);
  await shot(page, "portada-movil");
  await page.goto("/guia");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Guía para empezar");
  await page.goto("/privacidad");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Privacidad");
});

test("configura el local, la cámara y el video en vivo", async ({ page }) => {
  await login(page);

  await page.goto("/ajustes/local");
  await expect(page.getByRole("heading", { level: 2 }).first()).toBeVisible();
  if (await page.getByRole("heading", { name: "Registra tu local" }).isVisible()) {
    await page.getByLabel("Nombre").fill("Bar La Esquina");
    await page.getByLabel("Dirección").fill("Calle 10 # 5-20, Neiva");
    await page.getByRole("button", { name: "Registrar local" }).click();
  }

  const number = page.getByLabel("Número de WhatsApp");
  await number.fill("123");
  await page.getByRole("button", { name: "Guardar número" }).click();
  await expect(page.getByText("formato internacional")).toBeVisible();
  await page.getByLabel("Número de WhatsApp").fill("+57 300 000 0000");
  await page.getByRole("button", { name: "Guardar número" }).click();
  await expect(page.getByRole("status")).toContainText("Número guardado");
  await shot(page, "ajustes-local");

  await page.goto("/ajustes/camaras");
  await expect(page.getByLabel("Nombre")).toBeVisible();
  await page.waitForLoadState("networkidle");
  if (!(await page.getByRole("button", { name: "Eliminar" }).first().isVisible())) {
    await page.getByLabel("Nombre").fill("Barra principal");
    await page.getByLabel("Dirección RTSP").fill(RTSP_URL);
    await page.getByRole("button", { name: "Agregar cámara" }).click();
    await expect(page.getByRole("button", { name: "Eliminar" })).toBeVisible();
  }
  await expect(page.locator("body")).not.toContainText(RTSP_URL);
  await shot(page, "ajustes-camaras");

  await page.goto("/monitor");
  expect(await page.evaluate(() => window.crossOriginIsolated)).toBe(true);
  await expect(page.getByText(/En vivo a [1-9]\d* fps/)).toBeVisible({ timeout: 30_000 });
  await expect.poll(() => distinctPixels(page), { timeout: 15_000 }).toBeGreaterThan(20);
  await expect(page.getByText("Alertas activas")).toBeVisible();
  await shot(page, "monitor-en-vivo", false);
});

test("dos pestañas reciben el mismo incidente y la decisión es del operador", async ({ context }) => {
  const first = await context.newPage();
  await login(first);
  const second = await context.newPage();
  await second.goto("/monitor");

  await expect(first.getByRole("heading", { name: "Pelea" })).toBeVisible({ timeout: 15_000 });
  await expect(second.getByRole("heading", { name: "Pelea" })).toBeVisible({ timeout: 15_000 });
  await shot(first, "monitor-incidente", false);

  await first.getByRole("button", { name: "Confirmar y avisar al CAI" }).click();
  await expect(first.getByRole("dialog")).toContainText("+573000000000");
  await shot(first, "monitor-confirmacion", false);
  await first.getByRole("button", { name: "Sí, avisar al CAI" }).click();

  // Sin credenciales de WhatsApp en la prueba, el aviso debe fallar de forma visible.
  await expect(first.getByText("Falló el aviso")).toBeVisible({ timeout: 30_000 });
  await expect(second.getByText("Falló el aviso")).toBeVisible({ timeout: 30_000 });
  await expect(first.getByRole("button", { name: "Reintentar aviso" })).toBeVisible();

  await first.goto("/incidentes");
  await shot(first, "incidentes-lista");
  await first.getByRole("link", { name: /Pelea/ }).first().click();
  await expect(first.getByText("Por revisar")).toBeVisible();
  await expect(first.getByText("Falló el aviso")).toBeVisible();
  await shot(first, "incidente-detalle");
});

test("directorio y copia sin conexión", async ({ page, context }) => {
  await page.goto("/directorio");
  await expect(page.getByRole("heading", { name: "Los más buscados" })).toBeVisible();
  await expect(page.getByText("se presume inocente")).toBeVisible();
  if (DIRECTORY_SAMPLE) {
    await expect(async () => {
      await page.reload();
      await expect(page.getByText(DIRECTORY_SAMPLE)).toBeVisible({ timeout: 1_000 });
    }).toPass({ timeout: 90_000 });
    await page.getByRole("searchbox").fill("sin coincidencias");
    await expect(page.getByText("Ningún registro coincide")).toBeVisible();
    await page.getByRole("searchbox").fill("");
    await page.getByText(DIRECTORY_SAMPLE).click();
    await expect(page.getByRole("heading", { name: DIRECTORY_SAMPLE })).toBeVisible();
    await expect(page.getByRole("link", { name: "Llama al 123" })).toBeVisible();
    await shot(page, "directorio-ficha");
    await page.goto("/directorio");
  }
  await shot(page, "directorio-escritorio");
  await page.setViewportSize(MOBILE);
  await shot(page, "directorio-movil");

  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await page.waitForLoadState("networkidle");
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Los más buscados" })).toBeVisible();
  await page.goto("/guia").catch(() => undefined);
  await expect(page.getByRole("heading", { name: "No hay conexión" })).toBeVisible();
  await context.setOffline(false);
});
