import type { PublicQuestion, ResponseValue } from "../api/question";

export type Status = "unanswered" | "answered" | "marked";
type Q = Pick<PublicQuestion, "id" | "type"> & { required_count?: number; answer_length?: number };

/** O usuário já respondeu algo (o significado depende do tipo da questão). */
export function hasAnswer(q: Q, r: ResponseValue | undefined): boolean {
  if (!r) return false;
  switch (q.type) {
    case "multiple_choice":
    case "multiple_select":
    case "hot_area":
      return (r.selected ?? []).length > 0;
    case "build_list":
      return (r.sequence ?? []).length > 0;
    case "drag_drop":
      return Object.values(r.placements ?? {}).some((items) => items.length > 0);
    case "active_screen":
      return (r.events ?? []).length > 0;
    case "lab":
      return (r.events ?? []).length > 0 || (r.attested ?? []).length > 0;
    case "self_assessed":
      return r.self_mark !== null && r.self_mark !== undefined;
  }
}

/** A resposta está completa: respeita a quantidade exigida quando o tipo define uma. */
export function isComplete(q: Q, r: ResponseValue | undefined): boolean {
  if (!hasAnswer(q, r) || !r) return false;
  if (q.type === "multiple_select" || q.type === "hot_area") return (r.selected ?? []).length >= (q.required_count ?? 1);
  if (q.type === "build_list") return (r.sequence ?? []).length === (q.answer_length ?? 0);
  return true;
}

export function questionStatus(q: Q, r: ResponseValue | undefined, marked: boolean): Status {
  if (marked) return "marked";
  return hasAnswer(q, r) ? "answered" : "unanswered";
}
