import type { Kind, ResponseState } from "../api/types";

export type Status = "unanswered" | "answered" | "marked";
interface Q {
  id: string;
  kind: Kind;
  required_count?: number;
}

export function hasAnswer(q: Q, r: ResponseState | undefined): boolean {
  if (!r) return false;
  return q.kind === "interactive" ? r.self_mark !== null : r.selected.length > 0;
}

export function isComplete(q: Q, r: ResponseState | undefined): boolean {
  if (!hasAnswer(q, r) || !r) return false;
  return q.kind === "multiple" ? r.selected.length === (q.required_count ?? 1) : true;
}

export function questionStatus(q: Q, r: ResponseState | undefined, marked: boolean): Status {
  if (marked) return "marked";
  return hasAnswer(q, r) ? "answered" : "unanswered";
}
