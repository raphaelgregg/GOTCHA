import { useRef, useState } from "react";
import { api } from "../../api/client";
import type { HotShape, ImageBlock } from "../../api/question";
import { clamp01, svgProps, toNormalized, type Shape } from "../../lib/geometry";
import { Button } from "../ui";
import { nextId } from "./util";

type Tool = "select" | "rect" | "circle" | "polygon";
type Draft = { kind: "rect"; x0: number; y0: number; x1: number; y1: number } | { kind: "circle"; cx: number; cy: number; r: number } | { kind: "polygon"; points: Array<[number, number]> } | null;
const round = (v: number) => Math.round(v * 1000) / 1000;

function ShapeEl({ shape, aspect, cls }: { shape: Shape; aspect: number; cls: string }) {
  const p = svgProps(shape, aspect);
  const common = { className: cls, vectorEffect: "non-scaling-stroke" as const };
  if (shape.kind === "rect") return <rect {...p} {...common} />;
  if (shape.kind === "circle") return <circle {...p} {...common} />;
  return <polygon {...p} {...common} />;
}

/** Desenha e ajusta regiões diretamente sobre a imagem, em coordenadas normalizadas. */
export function RegionEditor({ image, aspect, shapes, correct, onChange }: {
  image: ImageBlock; aspect: number; shapes: HotShape[]; correct: string[];
  onChange: (next: { shapes: HotShape[]; correct: string[] }) => void;
}) {
  const [tool, setTool] = useState<Tool>("rect");
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(null);
  const drag = useRef<{ id: string; sx: number; sy: number; origin: Shape } | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const norm = (e: React.PointerEvent) => toNormalized(e.clientX, e.clientY, svg.current!.getBoundingClientRect());

  const add = (geometry: Shape) => {
    const id = nextId(shapes.map((s) => s.id), "r");
    onChange({ shapes: [...shapes, { id, label: `Região ${shapes.length + 1}`, geometry }], correct });
    setSelected(id);
    setTool("select");
  };
  const update = (id: string, geometry: Shape) => onChange({ shapes: shapes.map((s) => (s.id === id ? { ...s, geometry } : s)), correct });
  const finishPolygon = () => {
    if (draft?.kind === "polygon" && draft.points.length >= 3) add({ kind: "polygon", points: draft.points });
    setDraft(null);
  };

  const down = (e: React.PointerEvent) => {
    const [x, y] = norm(e);
    if (tool === "rect") { svg.current?.setPointerCapture(e.pointerId); setDraft({ kind: "rect", x0: x, y0: y, x1: x, y1: y }); }
    if (tool === "circle") { svg.current?.setPointerCapture(e.pointerId); setDraft({ kind: "circle", cx: x, cy: y, r: 0 }); }
    if (tool === "polygon") setDraft((d) => ({ kind: "polygon", points: [...(d?.kind === "polygon" ? d.points : []), [round(x), round(y)]] }));
  };
  const moveEv = (e: React.PointerEvent) => {
    const [x, y] = norm(e);
    if (draft?.kind === "rect") setDraft({ ...draft, x1: x, y1: y });
    if (draft?.kind === "circle") setDraft({ ...draft, r: Math.hypot(x - draft.cx, (y - draft.cy) * aspect) });
    if (drag.current) {
      const { id, sx, sy, origin } = drag.current;
      const dx = x - sx, dy = y - sy;
      if (origin.kind === "rect") update(id, { ...origin, x: round(clamp01(Math.min(origin.x + dx, 1 - origin.w))), y: round(clamp01(Math.min(origin.y + dy, 1 - origin.h))) });
      else if (origin.kind === "circle") update(id, { ...origin, cx: round(clamp01(origin.cx + dx)), cy: round(clamp01(origin.cy + dy)) });
      else update(id, { ...origin, points: origin.points.map(([px, py]) => [round(clamp01(px + dx)), round(clamp01(py + dy))] as [number, number]) });
    }
  };
  const up = () => {
    drag.current = null;
    if (draft?.kind === "rect") {
      const w = Math.abs(draft.x1 - draft.x0), h = Math.abs(draft.y1 - draft.y0);
      if (w > 0.01 && h > 0.01) add({ kind: "rect", x: round(Math.min(draft.x0, draft.x1)), y: round(Math.min(draft.y0, draft.y1)), w: round(w), h: round(h) });
      setDraft(null);
    }
    if (draft?.kind === "circle") {
      if (draft.r > 0.01) add({ kind: "circle", cx: round(draft.cx), cy: round(draft.cy), r: round(Math.min(draft.r, 1)) });
      setDraft(null);
    }
  };
  const startDrag = (e: React.PointerEvent, s: HotShape) => {
    if (tool !== "select") return;
    e.stopPropagation();
    setSelected(s.id);
    const [x, y] = norm(e);
    drag.current = { id: s.id, sx: x, sy: y, origin: s.geometry };
    svg.current?.setPointerCapture(e.pointerId);
  };

  const sel = shapes.find((s) => s.id === selected);
  const num = (label: string, value: number, key: string, g: Shape) => (
    <label key={key} className="field">{label}
      <input type="number" step={0.01} min={0} max={1} value={value} onChange={(e) => update(sel!.id, { ...g, [key]: clamp01(Number(e.target.value)) } as Shape)} />
    </label>
  );

  return (
    <div className="region-editor">
      <div className="seg" role="group" aria-label="Ferramenta">
        {(["select", "rect", "circle", "polygon"] as Tool[]).map((t) => (
          <button key={t} className={tool === t ? "is-on" : ""} onClick={() => { setTool(t); setDraft(null); }}>
            {{ select: "Selecionar/mover", rect: "Retângulo", circle: "Círculo", polygon: "Polígono" }[t]}
          </button>
        ))}
      </div>
      {tool === "polygon" && <p className="muted">Clique para marcar os pontos e use <strong>Concluir</strong> (mínimo 3). <Button variant="ghost" onClick={finishPolygon} disabled={!(draft?.kind === "polygon" && draft.points.length >= 3)}>Concluir polígono</Button></p>}
      <div className="hot-stage editable" style={{ aspectRatio: `1 / ${aspect}` }}>
        {image.asset ? <img src={api.assetUrl(image.asset)} alt={image.alt} draggable={false} /> : <div className="hot-missing">Escolha uma imagem acima para desenhar as regiões.</div>}
        <svg ref={svg} viewBox={`0 0 1 ${aspect}`} preserveAspectRatio="none" onPointerDown={down} onPointerMove={moveEv} onPointerUp={up} onKeyDown={(e) => e.key === "Escape" && setDraft(null)} role="application" aria-label="Área de desenho das regiões">
          {shapes.map((s) => (
            <g key={s.id} onPointerDown={(e) => startDrag(e, s)} onClick={() => tool === "select" && setSelected(s.id)}>
              <ShapeEl shape={s.geometry} aspect={aspect} cls={`hot-shape ${correct.includes(s.id) ? "is-correct" : ""} ${selected === s.id ? "is-selected" : ""}`} />
            </g>
          ))}
          {draft?.kind === "rect" && <rect className="hot-shape is-draft" vectorEffect="non-scaling-stroke" x={Math.min(draft.x0, draft.x1)} y={Math.min(draft.y0, draft.y1) * aspect} width={Math.abs(draft.x1 - draft.x0)} height={Math.abs(draft.y1 - draft.y0) * aspect} />}
          {draft?.kind === "circle" && <circle className="hot-shape is-draft" vectorEffect="non-scaling-stroke" cx={draft.cx} cy={draft.cy * aspect} r={draft.r} />}
          {draft?.kind === "polygon" && <polyline className="hot-shape is-draft" vectorEffect="non-scaling-stroke" fill="none" points={draft.points.map(([x, y]) => `${x},${y * aspect}`).join(" ")} />}
        </svg>
      </div>
      <ul className="shape-list">
        {shapes.map((s) => (
          <li key={s.id} className={selected === s.id ? "is-selected" : ""}>
            <label className="check" title="Região correta"><input type="checkbox" checked={correct.includes(s.id)} onChange={(e) => onChange({ shapes, correct: e.target.checked ? [...correct, s.id] : correct.filter((c) => c !== s.id) })} /> correta</label>
            <input value={s.label} aria-label="Nome da região" onChange={(e) => onChange({ shapes: shapes.map((x) => (x.id === s.id ? { ...x, label: e.target.value } : x)), correct })} onFocus={() => setSelected(s.id)} />
            <span className="muted">{s.geometry.kind}</span>
            <Button variant="ghost" aria-label="Remover região" onClick={() => onChange({ shapes: shapes.filter((x) => x.id !== s.id), correct: correct.filter((c) => c !== s.id) })}>✕</Button>
          </li>
        ))}
        {shapes.length === 0 && <li className="muted">Nenhuma região. Escolha uma ferramenta e desenhe sobre a imagem.</li>}
      </ul>
      {sel && sel.geometry.kind === "rect" && <div className="grid-3">{[["x", sel.geometry.x], ["y", sel.geometry.y], ["w", sel.geometry.w], ["h", sel.geometry.h]].map(([k, v]) => num(String(k), v as number, String(k), sel.geometry))}</div>}
      {sel && sel.geometry.kind === "circle" && <div className="grid-3">{[["cx", sel.geometry.cx], ["cy", sel.geometry.cy], ["r", sel.geometry.r]].map(([k, v]) => num(String(k), v as number, String(k), sel.geometry))}</div>}
    </div>
  );
}
