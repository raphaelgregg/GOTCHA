/** Atualiza a seleção de alternativas: escolha única substitui; múltipla alterna até o limite exigido. */
export function toggleChoice(selected: string[], id: string, multiple: boolean, required: number): string[] {
  if (!multiple) return [id];
  if (selected.includes(id)) return selected.filter((x) => x !== id);
  if (selected.length >= required) return selected;
  return [...selected, id].sort();
}
