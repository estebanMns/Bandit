import { afterEach, describe, expect, it, vi } from "vitest";
import { cached, clearCache, invalidate, peek } from "./cache";

afterEach(() => {
  clearCache();
  vi.useRealTimers();
});

describe("cached", () => {
  it("comparte una sola petición entre pedidos simultáneos", async () => {
    const load = vi.fn().mockResolvedValue(["local"]);

    const [a, b] = await Promise.all([cached("locales", load), cached("locales", load)]);

    expect(load).toHaveBeenCalledTimes(1);
    expect(a).toEqual(b);
  });

  it("sirve lo guardado mientras es reciente y vuelve a pedir cuando envejece", async () => {
    vi.useFakeTimers();
    const load = vi.fn().mockResolvedValueOnce(1).mockResolvedValueOnce(2);

    expect(await cached("n", load, 1000)).toBe(1);
    expect(await cached("n", load, 1000)).toBe(1);
    vi.advanceTimersByTime(1001);
    expect(peek("n")).toBe(1);
    expect(await cached("n", load, 1000)).toBe(2);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("un error no se guarda y conserva lo último bueno", async () => {
    vi.useFakeTimers();
    await cached("x", () => Promise.resolve("bueno"), 10);
    vi.advanceTimersByTime(11);

    await expect(cached("x", () => Promise.reject(new Error("caído")), 10)).rejects.toThrow();

    expect(peek("x")).toBe("bueno");
  });

  it("invalidar y vaciar olvidan los datos", async () => {
    await cached("establishments", () => Promise.resolve([1]));
    await cached("establishments:activity", () => Promise.resolve(2));
    await cached("me", () => Promise.resolve("admin"));

    invalidate("establishments");
    expect(peek("establishments")).toBeUndefined();
    expect(peek("establishments:activity")).toBeUndefined();
    expect(peek("me")).toBe("admin");

    clearCache();
    expect(peek("me")).toBeUndefined();
  });
});
