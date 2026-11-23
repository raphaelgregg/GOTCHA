import { describe, expect, it } from "vitest";
import vectors from "../../../tests/vectors/screen.json";
import { contains, type Shape } from "./geometry";
import { evaluate, LogicError } from "./logic";
import { replay, validateScreen, type ScreenEvent, type ScreenSpec } from "./screen";

describe("logic (JSON Logic subset, same rules as the server)", () => {
  const data = { ip: "10.0.0.5", n: 3, flag: true, tags: ["a", "b"] };
  it("evaluates operators", () => {
    expect(evaluate({ "==": [{ var: "ip" }, "10.0.0.5"] }, data)).toBe(true);
    expect(evaluate({ in: ["a", { var: "tags" }] }, data)).toBe(true);
    expect(evaluate({ ">": [{ var: "n" }, 2] }, data)).toBe(true);
    expect(evaluate({ "!": [{ var: "flag" }] }, data)).toBe(false);
  });
  it("is strict between bool and number", () => {
    expect(evaluate({ "==": [{ var: "x" }, 1] }, { x: true })).toBe(false);
  });
  it("rejects unknown operators", () => {
    expect(() => evaluate({ eval: ["1"] }, {})).toThrow(LogicError);
    expect(() => evaluate({ "==": [1] }, {})).toThrow(LogicError);
  });
  it("reads dotted paths and missing variables", () => {
    expect(evaluate({ var: "a.b" }, { a: { b: 7 } })).toBe(7);
    expect(evaluate({ var: "nope" }, {})).toBeNull();
  });
});

describe("geometry (normalized coordinates)", () => {
  const rect: Shape = { kind: "rect", x: 0.1, y: 0.2, w: 0.3, h: 0.2 };
  const circle: Shape = { kind: "circle", cx: 0.5, cy: 0.5, r: 0.1 };
  const poly: Shape = { kind: "polygon", points: [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.5, 0.5], [0.1, 0.9]] };
  it("rect", () => {
    expect(contains(rect, 0.2, 0.3)).toBe(true);
    expect(contains(rect, 0.5, 0.3)).toBe(false);
  });
  it("circle keeps its shape on tall images", () => {
    expect(contains(circle, 0.5, 0.54, 2)).toBe(true);
    expect(contains(circle, 0.5, 0.56, 2)).toBe(false);
  });
  it("concave polygon", () => {
    expect(contains(poly, 0.2, 0.2)).toBe(true);
    expect(contains(poly, 0.5, 0.8)).toBe(false);
  });
});

describe("screen engine parity with the server vectors", () => {
  for (const c of vectors as unknown as Array<{ name: string; spec: ScreenSpec; events: ScreenEvent[]; expect: { state: object; screen: string; ignored: number; messages?: string[] } }>) {
    it(c.name, () => {
      expect(validateScreen(c.spec)).toEqual([]);
      const run = replay(c.spec, c.events);
      expect(run.state).toEqual(c.expect.state);
      expect(run.screen).toBe(c.expect.screen);
      expect(run.ignored).toBe(c.expect.ignored);
      if (c.expect.messages) expect(run.messages).toEqual(c.expect.messages);
    });
  }
});
