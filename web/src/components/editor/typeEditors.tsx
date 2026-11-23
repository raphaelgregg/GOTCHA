import { useState, type ComponentType } from "react";
import { api } from "../../api/client";
import type { QType } from "../../api/question";
import { Button, Notice } from "../ui";
import { BlocksEditor, ImageEditor } from "./BlocksEditor";
import { RegionEditor } from "./RegionEditor";
import { ScreenEditor } from "./ScreenEditor";
import { lines, nextId, para, type EditorProps, type Q } from "./util";

function ChoiceEditor({ q, set }: EditorProps) {
  const multiple = q.type === "multiple_select";
  const options: Q[] = q.options;
  const correct: string[] = multiple ? q.correct : [q.correct];
  const setCorrect = (ids: string[]) => set({ correct: multiple ? ids : (ids[0] ?? "") });
  return (
    <div className="stack">
      {options.map((o, i) => (
        <div key={o.id} className="option-card">
          <div className="option-head">
            <label className="check" title="Alternativa correta">
              <input type={multiple ? "checkbox" : "radio"} name="correct" checked={correct.includes(o.id)}
                onChange={(e) => setCorrect(multiple ? (e.target.checked ? [...correct, o.id] : correct.filter((c) => c !== o.id)) : [o.id])} />
              <strong>{o.id}</strong> correta
            </label>
            <Button variant="ghost" aria-label="Remover alternativa" disabled={options.length <= 2} onClick={() => { set({ options: options.filter((_, k) => k !== i) }); setCorrect(correct.filter((c) => c !== o.id)); }}>✕</Button>
          </div>
          <BlocksEditor compact blocks={o.blocks} onChange={(blocks) => set({ options: options.map((x, k) => (k === i ? { ...x, blocks } : x)) })} />
        </div>
      ))}
      <Button variant="ghost" onClick={() => set({ options: [...options, { id: nextId(options.map((o) => o.id)), blocks: [para("")] }] })}>+ Alternativa</Button>
      {q.type === "multiple_choice" && (
        <label className="check"><input type="checkbox" checked={q.variant === "true_false"} onChange={(e) => set({ variant: e.target.checked ? "true_false" : "standard" })} /> Variante verdadeiro/falso</label>
      )}
      {multiple && <label className="check"><input type="checkbox" checked={Boolean(q.scoring?.partial)} onChange={(e) => set({ scoring: { ...q.scoring, partial: e.target.checked } })} /> Crédito parcial</label>}
    </div>
  );
}

function BuildListEditor({ q, set }: EditorProps) {
  const pool: Q[] = q.pool;
  const seq: string[] = q.answer_sequence;
  const setPos = (id: string, text: string) => {
    const pos = new Map<string, number>(seq.map((s, i) => [s, i + 1]));
    if (text === "") pos.delete(id); else pos.set(id, Number(text));
    set({ answer_sequence: [...pos.entries()].sort((a, b) => a[1] - b[1]).map(([k]) => k) });
  };
  return (
    <div className="stack">
      <p className="muted">Numere os itens na ordem correta. Itens sem número são iscas (aparecem, mas não fazem parte da sequência).</p>
      {pool.map((o, i) => (
        <div key={o.id} className="option-card">
          <div className="option-head">
            <label className="field inline">Posição<input type="number" min={1} max={pool.length} value={seq.indexOf(o.id) >= 0 ? seq.indexOf(o.id) + 1 : ""} onChange={(e) => setPos(o.id, e.target.value)} /></label>
            <Button variant="ghost" aria-label="Remover item" onClick={() => set({ pool: pool.filter((_, k) => k !== i), answer_sequence: seq.filter((s) => s !== o.id) })}>✕</Button>
          </div>
          <BlocksEditor compact blocks={o.blocks} onChange={(blocks) => set({ pool: pool.map((x, k) => (k === i ? { ...x, blocks } : x)) })} />
        </div>
      ))}
      <Button variant="ghost" onClick={() => set({ pool: [...pool, { id: nextId(pool.map((p) => p.id), "p"), blocks: [para("")] }] })}>+ Item</Button>
      <label className="check"><input type="checkbox" checked={Boolean(q.scoring?.partial)} onChange={(e) => set({ scoring: { ...q.scoring, partial: e.target.checked } })} /> Crédito parcial (por posição correta)</label>
    </div>
  );
}

function DragDropEditor({ q, set }: EditorProps) {
  const items: Q[] = q.items, targets: Q[] = q.targets, key: Record<string, string[]> = q.key;
  const toggle = (t: string, i: string, on: boolean) => set({ key: { ...key, [t]: on ? [...(key[t] ?? []), i] : (key[t] ?? []).filter((x) => x !== i) } });
  return (
    <div className="stack">
      <section className="subpanel">
        <h4>Itens arrastáveis</h4>
        {items.map((it, i) => (
          <div key={it.id} className="option-card">
            <div className="option-head">
              <label className="check"><input type="checkbox" checked={Boolean(it.reusable)} onChange={(e) => set({ items: items.map((x, k) => (k === i ? { ...x, reusable: e.target.checked } : x)) })} /> reutilizável</label>
              <Button variant="ghost" aria-label="Remover item" onClick={() => set({ items: items.filter((_, k) => k !== i), key: Object.fromEntries(Object.entries(key).map(([t, l]) => [t, l.filter((x) => x !== it.id)])) })}>✕</Button>
            </div>
            <BlocksEditor compact blocks={it.blocks} onChange={(blocks) => set({ items: items.map((x, k) => (k === i ? { ...x, blocks } : x)) })} />
          </div>
        ))}
        <Button variant="ghost" onClick={() => set({ items: [...items, { id: nextId(items.map((x) => x.id), "i"), blocks: [para("")], reusable: false }] })}>+ Item</Button>
      </section>
      <section className="subpanel">
        <h4>Destinos e gabarito</h4>
        {targets.map((t, i) => (
          <div key={t.id} className="option-card">
            <div className="option-head">
              <label className="field inline">Capacidade<input type="number" min={1} max={20} value={t.max_items} onChange={(e) => set({ targets: targets.map((x, k) => (k === i ? { ...x, max_items: Number(e.target.value) } : x)) })} /></label>
              <Button variant="ghost" aria-label="Remover destino" onClick={() => { const { [t.id]: _drop, ...rest } = key; set({ targets: targets.filter((_, k) => k !== i), key: rest }); }}>✕</Button>
            </div>
            <BlocksEditor compact blocks={t.blocks} onChange={(blocks) => set({ targets: targets.map((x, k) => (k === i ? { ...x, blocks } : x)) })} />
            <div className="chips-input"><span className="muted">Itens corretos:</span>
              {items.map((it) => <label key={it.id} className="chip"><input type="checkbox" checked={(key[t.id] ?? []).includes(it.id)} onChange={(e) => toggle(t.id, it.id, e.target.checked)} /> {it.id}</label>)}
            </div>
          </div>
        ))}
        <Button variant="ghost" onClick={() => { const id = nextId(targets.map((x) => x.id), "t"); set({ targets: [...targets, { id, blocks: [para("")], min_items: 0, max_items: 1 }], key: { ...key, [id]: [] } }); }}>+ Destino</Button>
        <label className="check"><input type="checkbox" checked={Boolean(q.ordered)} onChange={(e) => set({ ordered: e.target.checked })} /> A ordem dentro de cada destino importa</label>
        <label className="check"><input type="checkbox" checked={Boolean(q.scoring?.partial)} onChange={(e) => set({ scoring: { ...q.scoring, partial: e.target.checked } })} /> Crédito parcial (por destino)</label>
      </section>
    </div>
  );
}

function HotAreaEditor({ q, set }: EditorProps) {
  const [note, setNote] = useState<string | null>(null);
  const onImage = async (image: Q) => {
    set({ image });
    if (image.asset) {
      try {
        const info = await api.assetInfo(image.asset);
        if (info.width && info.height) {
          const aspect = Math.round((info.height / info.width) * 10000) / 10000;
          setNote(Math.abs(aspect - q.aspect) > 0.01 && q.shapes.length > 0 ? "A proporção da nova imagem é diferente: confira se as regiões ainda cobrem os pontos certos." : null);
          set({ image, aspect });
        }
      } catch { /* sem informações: mantém a proporção atual */ }
    }
  };
  return (
    <div className="stack">
      <ImageEditor block={q.image} onChange={(b) => void onImage(b)} />
      {note && <Notice tone="warn">{note}</Notice>}
      <div className="grid-2">
        <label className="field">Seleção
          <select value={q.selection?.mode ?? "single"} onChange={(e) => set({ selection: { ...q.selection, mode: e.target.value, required_count: null } })}>
            <option value="single">Uma região</option><option value="multiple">Várias regiões</option>
          </select>
        </label>
        <label className="check"><input type="checkbox" checked={Boolean(q.scoring?.partial)} onChange={(e) => set({ scoring: { ...q.scoring, partial: e.target.checked } })} /> Crédito parcial</label>
      </div>
      <RegionEditor image={q.image} aspect={q.aspect} shapes={q.shapes} correct={q.correct} onChange={(n) => set(n)} />
    </div>
  );
}

function SelfEditor({ q, set }: EditorProps) {
  return <BlocksEditor label="Resposta de referência (revelada ao usuário)" blocks={q.answer_blocks} onChange={(answer_blocks) => set({ answer_blocks })} />;
}

function LabEditor({ q, set }: EditorProps) {
  const steps: Q[] = q.steps;
  return (
    <div className="stack">
      <label className="field">Tipo de laboratório
        <select value={q.mode} onChange={async (e) => set(await api.convert("lab", q, e.target.value))}>
          <option value="simulated">Simulado (roda no GOTCHA)</option>
          <option value="external_instructions">Instruções de laboratório externo</option>
          <option value="real">Laboratório real (somente descrição)</option>
        </select>
      </label>
      <Notice tone="warn">{q.mode === "simulated" ? "Uma simulação local nunca é apresentada como execução real de infraestrutura." : "O GOTCHA não executa nem acessa este ambiente. A pontuação é autoavaliada."}</Notice>
      <label className="field">Objetivos (um por linha)<textarea rows={3} value={q.objectives.join("\n")} onChange={(e) => set({ objectives: lines(e.target.value) })} /></label>
      <label className="field">Recursos necessários (um por linha)<textarea rows={2} value={(q.resources ?? []).join("\n")} onChange={(e) => set({ resources: lines(e.target.value) })} /></label>
      <label className="field">Ambiente<input value={q.environment?.description ?? ""} onChange={(e) => set({ environment: { ...q.environment, description: e.target.value } })} /></label>
      <section className="subpanel">
        <h4>Etapas</h4>
        {steps.map((s, i) => (
          <div key={s.id} className="option-card">
            <div className="option-head"><input value={s.title} aria-label="Título da etapa" onChange={(e) => set({ steps: steps.map((x, k) => (k === i ? { ...x, title: e.target.value } : x)) })} />
              <Button variant="ghost" aria-label="Remover etapa" onClick={() => set({ steps: steps.filter((_, k) => k !== i) })}>✕</Button></div>
            <BlocksEditor compact blocks={s.instructions} onChange={(instructions) => set({ steps: steps.map((x, k) => (k === i ? { ...x, instructions } : x)) })} />
          </div>
        ))}
        <Button variant="ghost" onClick={() => set({ steps: [...steps, { id: nextId(steps.map((s) => s.id), "etapa"), title: `Etapa ${steps.length + 1}`, instructions: [para("")] }] })}>+ Etapa</Button>
      </section>
      {q.mode === "simulated" && q.screen && <ScreenEditor q={q} set={set} />}
    </div>
  );
}

/** Um editor por tipo; o editor universal escolhe o painel pelo tipo da questão. */
export const EDITORS: Record<QType, ComponentType<EditorProps>> = {
  multiple_choice: ChoiceEditor,
  multiple_select: ChoiceEditor,
  build_list: BuildListEditor,
  drag_drop: DragDropEditor,
  hot_area: HotAreaEditor,
  active_screen: ScreenEditor,
  lab: LabEditor,
  self_assessed: SelfEditor,
};
