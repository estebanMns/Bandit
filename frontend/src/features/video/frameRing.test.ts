import { describe, expect, it } from "vitest";
import { FrameRing, frameRingBytes } from "./frameRing";

const WIDTH = 2;
const HEIGHT = 2;
const PIXELS = WIDTH * HEIGHT * 4;

function ring(): FrameRing {
  return new FrameRing(new SharedArrayBuffer(frameRingBytes(WIDTH, HEIGHT)), WIDTH, HEIGHT);
}

function frame(value: number): Uint8ClampedArray {
  return new Uint8ClampedArray(PIXELS).fill(value);
}

function read(target: FrameRing): Uint8ClampedArray {
  const copy = new Uint8ClampedArray(PIXELS);
  target.copyLatestInto(copy);
  return copy;
}

describe("FrameRing", () => {
  it("no informa fotogramas antes de la primera escritura", () => {
    expect(ring().latest()).toBeNull();
  });

  it("entrega el fotograma publicado con sus dimensiones", () => {
    const target = ring();

    target.write(frame(7), WIDTH, HEIGHT);

    expect(target.latest()).toEqual({ sequence: 1, width: WIDTH, height: HEIGHT });
    expect(read(target).every((value) => value === 7)).toBe(true);
  });

  it("siempre muestra el más reciente tras dar la vuelta al búfer", () => {
    const target = ring();

    for (let value = 1; value <= 7; value += 1) target.write(frame(value), WIDTH, HEIGHT);

    expect(target.latest()?.sequence).toBe(7);
    expect(read(target).every((value) => value === 7)).toBe(true);
  });

  it("nunca escribe sobre el espacio publicado", () => {
    const buffer = new SharedArrayBuffer(frameRingBytes(WIDTH, HEIGHT));
    const writer = new FrameRing(buffer, WIDTH, HEIGHT);
    const reader = new FrameRing(buffer, WIDTH, HEIGHT);
    writer.write(frame(1), WIDTH, HEIGHT);
    const published = read(reader);

    writer.write(frame(2), WIDTH, HEIGHT);

    expect(published.every((value) => value === 1)).toBe(true);
    expect(read(reader).every((value) => value === 2)).toBe(true);
  });

  it("rechaza fotogramas más grandes que el espacio reservado", () => {
    expect(() => ring().write(new Uint8ClampedArray(PIXELS + 1), 3, 3)).toThrow(RangeError);
  });
});
