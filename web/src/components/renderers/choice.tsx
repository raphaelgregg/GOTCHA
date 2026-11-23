import { toggleChoice } from "../../lib/choices";
import { BlockView } from "../BlockView";
import { letter, type Of, type RendererProps } from "./types";

export function ChoiceRenderer({ q, value, onChange, locked, solution }: RendererProps<Of<"multiple_choice"> | Of<"multiple_select">>) {
  const selected = value?.selected ?? [];
  const multiple = q.type === "multiple_select";
  const key = solution?.key?.correct;
  const correct = new Set<string>(Array.isArray(key) ? (key as string[]) : key ? [key as string] : []);
  return (
    <fieldset className="choices" disabled={locked}>
      <legend className="sr-only">Alternativas</legend>
      {q.options.map((o, i) => {
        const checked = selected.includes(o.id);
        const state = solution ? (correct.has(o.id) ? "is-correct" : checked ? "is-wrong" : "") : "";
        return (
          <label key={o.id} className={`choice ${checked ? "is-selected" : ""} ${state}`}>
            <input type={multiple ? "checkbox" : "radio"} name={`q-${q.id}`} checked={checked}
              onChange={() => onChange({ selected: toggleChoice(selected, o.id, multiple, q.required_count) })} />
            <span className="choice-letter">{letter(i)}</span>
            <span className="choice-text"><BlockView blocks={o.blocks} inline /></span>
          </label>
        );
      })}
    </fieldset>
  );
}
