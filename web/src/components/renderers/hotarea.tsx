import { api } from "../../api/client";
import { svgProps } from "../../lib/geometry";
import { Notice } from "../ui";
import type { Of, RendererProps } from "./types";

export function HotAreaRenderer({ q, value, onChange, locked, solution }: RendererProps<Of<"hot_area">>) {
  const selected = value?.selected ?? [];
  const correct = new Set<string>((solution?.key?.correct as string[] | undefined) ?? []);
  const multiple = q.selection.mode === "multiple";
  const toggle = (id: string) => {
    if (locked) return;
    if (!multiple) return onChange({ selected: selected.includes(id) ? [] : [id] });
    if (selected.includes(id)) return onChange({ selected: selected.filter((x) => x !== id) });
    if (selected.length < q.selection.required_count) onChange({ selected: [...selected, id].sort() });
  };
  return (
    <div className="hotarea">
      {multiple && <p className="muted">Selecione {q.selection.required_count} região(ões).</p>}
      <div className="hot-stage" style={{ aspectRatio: `1 / ${q.aspect}` }}>
        {q.image.asset ? <img src={api.assetUrl(q.image.asset)} alt={q.image.alt} draggable={false} /> : <div className="hot-missing">Imagem ausente: {q.image.name || "sem nome"}</div>}
        <svg viewBox={`0 0 1 ${q.aspect}`} preserveAspectRatio="none" role="group" aria-label="Regiões clicáveis">
          {q.shapes.map((s) => {
            const on = selected.includes(s.id);
            const state = solution ? (correct.has(s.id) ? "is-correct" : on ? "is-wrong" : "") : on ? "is-on" : "";
            const props = svgProps(s.geometry, q.aspect);
            const common = { className: `hot-shape ${state}`, vectorEffect: "non-scaling-stroke" as const };
            return (
              <g key={s.id} role="button" tabIndex={locked ? -1 : 0} aria-pressed={on} aria-label={s.label || s.id}
                onClick={() => toggle(s.id)} onKeyDown={(e) => (e.key === " " || e.key === "Enter") && (e.preventDefault(), toggle(s.id))}>
                {s.geometry.kind === "rect" && <rect {...props} {...common} />}
                {s.geometry.kind === "circle" && <circle {...props} {...common} />}
                {s.geometry.kind === "polygon" && <polygon {...props} {...common} />}
              </g>
            );
          })}
        </svg>
      </div>
      {!q.image.asset && <Notice tone="warn">A imagem desta questão está ausente. Corrija no editor.</Notice>}
    </div>
  );
}
