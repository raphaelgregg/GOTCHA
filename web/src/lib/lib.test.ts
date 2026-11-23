import { describe, expect, it } from "vitest";
import { toggleChoice } from "./choices";
import { formatClock, formatPct, formatDuration, plural } from "./format";
import { hasAnswer, isComplete, questionStatus } from "./progress";
import { parseHash, buildHash } from "./route";

describe("toggleChoice", () => {
  it("single choice replaces the selection", () => {
    expect(toggleChoice(["A"], "B", false, 1)).toEqual(["B"]);
  });
  it("multiple adds and removes ids, keeping them sorted", () => {
    expect(toggleChoice(["C"], "A", true, 3)).toEqual(["A", "C"]);
    expect(toggleChoice(["A", "C"], "A", true, 3)).toEqual(["C"]);
  });
  it("multiple ignores selections beyond the required count", () => {
    expect(toggleChoice(["A", "B"], "C", true, 2)).toEqual(["A", "B"]);
  });
});

describe("progress by question type", () => {
  const q = (o: object) => o as never;
  it("choice types need a selection; multiple select needs the exact count", () => {
    const ms = q({ id: "m", type: "multiple_select", required_count: 2 });
    expect(hasAnswer(ms, { selected: ["A"] })).toBe(true);
    expect(isComplete(ms, { selected: ["A"] })).toBe(false);
    expect(isComplete(ms, { selected: ["A", "B"] })).toBe(true);
  });
  it("build list is complete when the sequence has the expected length", () => {
    const b = q({ id: "b", type: "build_list", answer_length: 3 });
    expect(hasAnswer(b, { sequence: ["x"] })).toBe(true);
    expect(isComplete(b, { sequence: ["x", "y"] })).toBe(false);
    expect(isComplete(b, { sequence: ["x", "y", "z"] })).toBe(true);
  });
  it("drag and drop is answered when anything was placed", () => {
    const d = q({ id: "d", type: "drag_drop" });
    expect(hasAnswer(d, { placements: { t1: [] } })).toBe(false);
    expect(hasAnswer(d, { placements: { t1: ["i1"] } })).toBe(true);
  });
  it("hot area, screens and labs", () => {
    expect(hasAnswer(q({ id: "h", type: "hot_area" }), { selected: ["s1"] })).toBe(true);
    expect(hasAnswer(q({ id: "a", type: "active_screen" }), { events: [] })).toBe(false);
    expect(hasAnswer(q({ id: "a", type: "active_screen" }), { events: [{ component: "x", type: "click" }] })).toBe(true);
    expect(hasAnswer(q({ id: "l", type: "lab" }), { attested: ["s1"] })).toBe(true);
  });
  it("self assessed is answered by the mark, including a negative one", () => {
    const s = q({ id: "s", type: "self_assessed" });
    expect(hasAnswer(s, { self_mark: false })).toBe(true);
    expect(hasAnswer(s, {})).toBe(false);
  });
  it("status is unanswered, answered or marked", () => {
    const mc = q({ id: "c", type: "multiple_choice" });
    expect(questionStatus(mc, undefined, false)).toBe("unanswered");
    expect(questionStatus(mc, { selected: ["A"] }, false)).toBe("answered");
    expect(questionStatus(mc, undefined, true)).toBe("marked");
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
  it("knows the editor routes", () => {
    expect(parseHash("#/questions/e1").name).toBe("questions");
    expect(parseHash("#/question/q_abc")).toEqual({ name: "question", id: "q_abc", query: {} });
    expect(parseHash("#/case/c1").name).toBe("case");
  });
  it("builds hashes", () => {
    expect(buildHash("batch", "z")).toBe("#/batch/z");
    expect(buildHash("library")).toBe("#/");
    expect(buildHash("simulado", "new", { exam: "e1" })).toBe("#/simulado/new?exam=e1");
  });
});
