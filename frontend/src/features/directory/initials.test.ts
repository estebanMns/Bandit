import { describe, expect, it } from "vitest";
import { initials } from "./initials";

describe("initials", () => {
  it("toma la primera letra del primer y del último nombre", () => {
    expect(initials("Jhon Edwin Tenorio Chocue")).toBe("JC");
    expect(initials("  ana  ")).toBe("A");
    expect(initials("")).toBe("?");
  });
});
