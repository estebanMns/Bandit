/**
 * Búfer circular de fotogramas RGBA sobre SharedArrayBuffer.
 *
 * Un solo escritor (Web Worker) y un solo lector (hilo principal). El escritor
 * llena un espacio distinto del publicado y luego publica su índice con Atomics,
 * así el lector nunca ve un fotograma a medio escribir, salvo que tarde más que
 * dos fotogramas completos en copiar uno.
 */

const SLOTS = 3;
const PUBLISHED = 0;
const SEQUENCE = 1;
const HEADER_FIELDS = 2 + SLOTS * 2;
const HEADER_BYTES = HEADER_FIELDS * Int32Array.BYTES_PER_ELEMENT;
const BYTES_PER_PIXEL = 4;

export const MAX_FRAME_WIDTH = 1280;
export const MAX_FRAME_HEIGHT = 960;

function slotBytes(maxWidth: number, maxHeight: number): number {
  return maxWidth * maxHeight * BYTES_PER_PIXEL;
}

export function frameRingBytes(
  maxWidth: number = MAX_FRAME_WIDTH,
  maxHeight: number = MAX_FRAME_HEIGHT,
): number {
  return HEADER_BYTES + SLOTS * slotBytes(maxWidth, maxHeight);
}

export interface FrameInfo {
  sequence: number;
  width: number;
  height: number;
}

export class FrameRing {
  private readonly header: Int32Array;
  private readonly slots: Uint8ClampedArray[];

  constructor(
    buffer: SharedArrayBuffer | ArrayBuffer,
    maxWidth: number = MAX_FRAME_WIDTH,
    maxHeight: number = MAX_FRAME_HEIGHT,
  ) {
    const size = slotBytes(maxWidth, maxHeight);
    this.header = new Int32Array(buffer, 0, HEADER_FIELDS);
    this.slots = Array.from(
      { length: SLOTS },
      (_, index) => new Uint8ClampedArray(buffer, HEADER_BYTES + index * size, size),
    );
  }

  write(pixels: Uint8ClampedArray, width: number, height: number): void {
    const sequence = Atomics.load(this.header, SEQUENCE) + 1;
    const slotIndex = sequence % SLOTS;
    const slot = this.slots[slotIndex];
    if (!slot || pixels.length > slot.length) {
      throw new RangeError("El fotograma no cabe en el búfer");
    }
    slot.set(pixels);
    Atomics.store(this.header, 2 + slotIndex * 2, width);
    Atomics.store(this.header, 3 + slotIndex * 2, height);
    Atomics.store(this.header, PUBLISHED, slotIndex);
    Atomics.store(this.header, SEQUENCE, sequence);
    Atomics.notify(this.header, SEQUENCE);
  }

  latest(): FrameInfo | null {
    const sequence = Atomics.load(this.header, SEQUENCE);
    if (sequence === 0) return null;
    const slotIndex = Atomics.load(this.header, PUBLISHED);
    return {
      sequence,
      width: Atomics.load(this.header, 2 + slotIndex * 2),
      height: Atomics.load(this.header, 3 + slotIndex * 2),
    };
  }

  /** Copia el último fotograma: `ImageData` no acepta memoria compartida. */
  copyLatestInto(target: Uint8ClampedArray): void {
    const slotIndex = Atomics.load(this.header, PUBLISHED);
    const slot = this.slots[slotIndex];
    if (slot) target.set(slot.subarray(0, target.length));
  }
}
