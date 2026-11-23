import { describe, expect, it } from "vitest";
import { toggleChoice } from "./choices";
import { formatClock, formatPct, formatDuration, plural } from "./format";
import { questionStatus, isComplete } from "./progress";
import { parseHash, buildHash } from "./route";

describe("toggleChoice", () => {
  it("single choice replaces the selection", () => {
    expect(toggleChoice(["A"], "B", "single", 1)).toEqual(["B"]);
  });
  it("true/false behaves like single choice", () => {
    expect(toggleChoice([], "A", "true_false", 1)).toEqual(["A"]);
  });
  it("multiple adds and removes letters, keeping them sorted", () => {
    expect(toggleChoice(["C"], "A", "multiple", 3)).toEqual(["A", "C"]);
    expect(toggleChoice(["A", "C"], "A", "multiple", 3)).toEqual(["C"]);
  });
  it("multiple ignores selections beyond the required count", () => {
    expect(toggleChoice(["A", "B"], "C", "multiple", 2)).toEqual(["A", "B"]);
  });
});

describe("progress", () => {
  const q = { id: "q", kind: "multiple", required_count: 2 } as const;
  it("status is unanswered, answered or marked", () => {
    expect(questionStatus(q, undefined, false)).toBe("unanswered");
    expect(questionStatus(q, { selected: ["A"], self_mark: null }, false)).toBe("answered");
    expect(questionStatus(q, undefined, true)).toBe("marked");
  });
  it("interactive questions are answered by the self mark", () => {
    const i = { id: "i", kind: "interactive" } as const;
    expect(questionStatus(i, { selected: [], self_mark: false }, false)).toBe("answered");
  });
  it("multiple is complete only with the exact count", () => {
    expect(isComplete(q, { selected: ["A"], self_mark: null })).toBe(false);
    expect(isComplete(q, { selected: ["A", "B"], self_mark: null })).toBe(true);
  });
});

describe("format", () => {
  it("formats the clock", () => {
    expect(formatClock(65)).toBe("01:05");
    expect(formatClock(3725)).toBe("1:02:05");
    expect(formatClock(0)).toBe("00:00");
  });
  it("formats percentages in pt-BR and handles null", () => {
    expect(formatPct(66.7)).toBe("66,7%");
    expect(formatPct(100)).toBe("100%");
    expect(formatPct(null)).toBe("—");
  });
  it("formats durations for humans", () => {
    expect(formatDuration(59)).toBe("59 s");
    expect(formatDuration(125)).toBe("2 min 5 s");
    expect(formatDuration(3660)).toBe("1 h 1 min");
  });
});

describe("plural", () => {
  it("uses singular for 1 and plural otherwise", () => {
    expect(plural(1, "aviso", "avisos")).toBe("1 aviso");
    expect(plural(0, "aviso", "avisos")).toBe("0 avisos");
    expect(plural(34, "aviso", "avisos")).toBe("34 avisos");
  });
});

describe("route", () => {
  it("parses hash routes with params and query", () => {
    expect(parseHash("#/exam/abc?x=1")).toEqual({ name: "exam", id: "abc", query: { x: "1" } });
    expect(parseHash("#/")).toEqual({ name: "library", id: null, query: {} });
    expect(parseHash("")).toEqual({ name: "library", id: null, query: {} });
    expect(parseHash("#/simulado/new?exam=e1")).toEqual({
      name: "simulado", id: "new", query: { exam: "e1" },
    });
  });
  it("builds hashes", () => {
    expect(buildHash("batch", "z")).toBe("#/batch/z");
    expect(buildHash("library")).toBe("#/");
    expect(buildHash("simulado", "new", { exam: "e1" })).toBe("#/simulado/new?exam=e1");
  });
});
