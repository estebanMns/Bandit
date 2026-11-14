import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { backendSocketUrl } from "./socket-url";

function answer(status: number, body: unknown = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body }),
  );
}

beforeEach(() => {
  vi.stubGlobal("location", { protocol: "https:", host: "bandit-ruddy.vercel.app" });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("backendSocketUrl", () => {
  it("usa la dirección que anuncia el backend, con el ticket", async () => {
    answer(200, { ticket: "t/1", ws_url: "wss://bandit-api.onrender.com" });

    expect(await backendSocketUrl("/ws/events/x")).toBe(
      "wss://bandit-api.onrender.com/ws/events/x?ticket=t%2F1",
    );
  });

  it("sin dirección del backend se conecta al mismo dominio con el ticket", async () => {
    answer(200, { ticket: "t" });

    expect(await backendSocketUrl("/ws/video/c")).toBe("wss://bandit-ruddy.vercel.app/ws/video/c");
  });

  it("sin sesión vuelve al mismo dominio", async () => {
    answer(401);

    expect(await backendSocketUrl("/ws/events/x")).toBe(
      "wss://bandit-ruddy.vercel.app/ws/events/x",
    );
  });
});
