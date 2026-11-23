import type { Kind } from "../api/types";

/** Atualiza a seleção de alternativas conforme o tipo de questão. */
export function toggleChoice(
  selected: string[],
  letter: string,
  kind: Kind,
  required: number,
): string[] {
  if (kind !== "multiple") return [letter];
  if (selected.includes(letter)) return selected.filter((l) => l !== letter);
  if (selected.length >= required) return selected;
  return [...selected, letter].sort();
}
