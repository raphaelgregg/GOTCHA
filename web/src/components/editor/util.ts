import type { Block } from "../../api/question";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Q = Record<string, any>;
export interface EditorProps {
  q: Q;
  set: (patch: Q) => void;
}

/** Próximo identificador livre (A, B, C… ou prefixo + número). */
export function nextId(taken: string[], prefix?: string): string {
  if (!prefix) {
    for (let i = 0; i < 26; i++) {
      const id = String.fromCharCode(65 + i);
      if (!taken.includes(id)) return id;
    }
  }
  const p = prefix ?? "x";
  let n = taken.length + 1;
  while (taken.includes(`${p}${n}`)) n++;
  return `${p}${n}`;
}

export const para = (text = ""): Block => ({ type: "paragraph", text });
export const lines = (text: string): string[] => text.split("\n").map((l) => l.trim()).filter(Boolean);
export const move = <T,>(list: T[], from: number, to: number): T[] => {
  if (to < 0 || to >= list.length) return list;
  const next = [...list];
  next.splice(to, 0, ...next.splice(from, 1));
  return next;
};

/** Converte texto digitado em valor JSON simples (true, 12, "texto"). */
export function parseValue(text: string): unknown {
  const t = text.trim();
  if (t === "true") return true;
  if (t === "false") return false;
  if (t !== "" && !Number.isNaN(Number(t))) return Number(t);
  return text;
}
export const showValue = (v: unknown): string => (typeof v === "string" ? v : JSON.stringify(v));
