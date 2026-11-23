import { Button } from "../ui";
import { BlocksEditor } from "./BlocksEditor";
import { lines, nextId, parseValue, showValue, type EditorProps, type Q } from "./util";

const OPS = ["==", "!=", ">", "<", ">=", "<=", "in"];
const TYPES = ["text", "button", "input", "select", "checkbox", "radio_group", "tabs", "menu", "table", "toggle"];

type Row = { var: string; op: string; value: string };

/** Construtor de condições: uma ou mais comparações ligadas por E, convertidas para JSON Logic. */
export function ConditionBuilder({ expr, vars, onChange, label }: { expr: unknown; vars: string[]; onChange: (e: unknown) => void; label: string }) {
  const rows: Row[] = toRows(expr);
  const emit = (next: Row[]) => onChange(next.length === 0 ? null : next.length === 1 ? toLogic(next[0]!) : { and: next.map(toLogic) });
  return (
    <div className="cond">
      <span className="muted">{label}</span>
      {rows.map((r, i) => (
        <div key={i} className="cond-row">
          <select value={r.var} aria-label="Variável" onChange={(e) => emit(rows.map((x, k) => (k === i ? { ...x, var: e.target.value } : x)))}>
            {vars.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select value={r.op} aria-label="Operador" onChange={(e) => emit(rows.map((x, k) => (k === i ? { ...x, op: e.target.value } : x)))}>{OPS.map((o) => <option key={o}>{o}</option>)}</select>
          <input value={r.value} aria-label="Valor" onChange={(e) => emit(rows.map((x, k) => (k === i ? { ...x, value: e.target.value } : x)))} />
          <Button variant="ghost" aria-label="Remover condição" onClick={() => emit(rows.filter((_, k) => k !== i))}>✕</Button>
        </div>
      ))}
      <Button variant="ghost" disabled={vars.length === 0} onClick={() => emit([...rows, { var: vars[0] ?? "", op: "==", value: "" }])}>+ Condição</Button>
    </div>
  );
}
const toLogic = (r: Row): unknown => ({ [r.op]: [{ var: r.var }, parseValue(r.value)] });
function toRows(expr: unknown): Row[] {
  const one = (e: unknown): Row | null => {
    if (!e || typeof e !== "object") return null;
    const [op, args] = Object.entries(e as Record<string, unknown>)[0] ?? [];
    if (!op || !OPS.includes(op) || !Array.isArray(args)) return null;
    const v = args[0] as { var?: string } | undefined;
    return v && typeof v === "object" && typeof v.var === "string" ? { var: v.var, op, value: showValue(args[1]) } : null;
  };
  if (!expr) return [];
  const e = expr as { and?: unknown[] };
  if (Array.isArray(e.and)) return e.and.map(one).filter((r): r is Row => r !== null);
  const r = one(expr);
  return r ? [r] : [];
}

function ActionsEditor({ actions, vars, screens, onChange }: { actions: Q[]; vars: string[]; screens: string[]; onChange: (a: Q[]) => void }) {
  return (
    <div className="actions-editor">
      {actions.map((a, i) => (
        <div key={i} className="cond-row">
          <select value={a.do} aria-label="Ação" onChange={(e) => onChange(actions.map((x, k) => (k === i ? { do: e.target.value, var: vars[0], screen: screens[0], text: "Mensagem", value: true } : x)))}>
            {["set", "toggle", "append", "goto", "message"].map((d) => <option key={d}>{d}</option>)}
          </select>
          {["set", "toggle", "append"].includes(a.do) && <select value={a.var ?? ""} aria-label="Variável" onChange={(e) => onChange(actions.map((x, k) => (k === i ? { ...x, var: e.target.value } : x)))}>{vars.map((v) => <option key={v}>{v}</option>)}</select>}
          {["set", "append"].includes(a.do) && <input value={showValue(a.value)} aria-label="Valor" onChange={(e) => onChange(actions.map((x, k) => (k === i ? { ...x, value: parseValue(e.target.value) } : x)))} />}
          {a.do === "goto" && <select value={a.screen ?? ""} aria-label="Tela" onChange={(e) => onChange(actions.map((x, k) => (k === i ? { ...x, screen: e.target.value } : x)))}>{screens.map((s) => <option key={s}>{s}</option>)}</select>}
          {a.do === "message" && <input value={a.text ?? ""} aria-label="Texto" onChange={(e) => onChange(actions.map((x, k) => (k === i ? { ...x, text: e.target.value } : x)))} />}
          <Button variant="ghost" aria-label="Remover ação" onClick={() => onChange(actions.filter((_, k) => k !== i))}>✕</Button>
        </div>
      ))}
      <Button variant="ghost" onClick={() => onChange([...actions, { do: "set", var: vars[0], value: true }])} disabled={vars.length === 0}>+ Ação</Button>
    </div>
  );
}

const optionsText = (opts: Q[] = []) => opts.map((o) => `${o.id}: ${o.label ?? ""}`).join("\n");
const parseOptions = (t: string) => lines(t).map((l) => { const [id, ...rest] = l.split(":"); return { id: id!.trim(), label: rest.join(":").trim() }; });

/** Editor declarativo de telas: estado, telas, componentes, ações e verificações (sem código). */
export function ScreenEditor({ q, set }: EditorProps) {
  const screen: Q = q.screen;
  const vars = Object.keys(screen.state ?? {});
  const screenIds: string[] = screen.screens.map((s: Q) => s.id);
  const setScreen = (patch: Q) => set({ screen: { ...screen, ...patch } });
  const setComp = (si: number, ci: number, patch: Q) => setScreen({ screens: screen.screens.map((s: Q, i: number) => (i !== si ? s : { ...s, components: s.components.map((c: Q, k: number) => (k === ci ? { ...c, ...patch } : c)) })) });
  const checks: Q[] = q.checks ?? [];
  const setChecks = (next: Q[]) => set({ checks: next, completion: next.length ? { and: next.map((c) => c.when) } : null });

  return (
    <div className="stack">
      <section className="subpanel">
        <h4>Variáveis de estado</h4>
        {vars.map((name) => (
          <div key={name} className="cond-row">
            <input value={name} aria-label="Nome" readOnly />
            <select value={screen.state[name].type} aria-label="Tipo" onChange={(e) => setScreen({ state: { ...screen.state, [name]: { type: e.target.value, initial: undefined } } })}>
              {["string", "number", "bool", "list"].map((t) => <option key={t}>{t}</option>)}
            </select>
            <input value={showValue(screen.state[name].initial ?? "")} aria-label="Valor inicial" onChange={(e) => setScreen({ state: { ...screen.state, [name]: { ...screen.state[name], initial: parseValue(e.target.value) } } })} />
            <Button variant="ghost" aria-label="Remover variável" onClick={() => { const { [name]: _drop, ...rest } = screen.state; setScreen({ state: rest }); }}>✕</Button>
          </div>
        ))}
        <Button variant="ghost" onClick={() => setScreen({ state: { ...screen.state, [nextId(vars, "var")]: { type: "string", initial: "" } } })}>+ Variável</Button>
      </section>

      {screen.screens.map((s: Q, si: number) => (
        <section key={s.id} className="subpanel">
          <div className="row-between">
            <h4>Tela <input className="inline-input" value={s.id} aria-label="Identificador da tela" readOnly /> <input className="inline-input" value={s.title ?? ""} aria-label="Título da tela" onChange={(e) => setScreen({ screens: screen.screens.map((x: Q, i: number) => (i === si ? { ...x, title: e.target.value } : x)) })} /></h4>
            <label className="check"><input type="radio" name="start" checked={screen.start === s.id} onChange={() => setScreen({ start: s.id })} /> inicial</label>
          </div>
          {s.components.map((c: Q, ci: number) => (
            <div key={c.id} className="component-card">
              <div className="cond-row">
                <input value={c.id} readOnly aria-label="Identificador" />
                <select value={c.type} aria-label="Tipo de componente" onChange={(e) => setComp(si, ci, { type: e.target.value })}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select>
                <input value={c.label ?? ""} aria-label="Rótulo" placeholder="Rótulo" onChange={(e) => setComp(si, ci, { label: e.target.value })} />
                {["input", "select", "checkbox", "radio_group", "tabs", "table", "toggle"].includes(c.type) && (
                  <select value={c.bind ?? ""} aria-label="Variável ligada" onChange={(e) => setComp(si, ci, { bind: e.target.value || null })}><option value="">(sem variável)</option>{vars.map((v) => <option key={v}>{v}</option>)}</select>
                )}
                <Button variant="ghost" aria-label="Remover componente" onClick={() => setScreen({ screens: screen.screens.map((x: Q, i: number) => (i === si ? { ...x, components: x.components.filter((_: Q, k: number) => k !== ci) } : x)) })}>✕</Button>
              </div>
              {c.type === "text" && <input value={c.text ?? ""} aria-label="Texto" placeholder="Texto exibido" onChange={(e) => setComp(si, ci, { text: e.target.value })} />}
              {["select", "radio_group", "tabs"].includes(c.type) && <textarea rows={3} aria-label="Opções (id: rótulo)" placeholder="id: rótulo, uma por linha" value={optionsText(c.options)} onChange={(e) => setComp(si, ci, { options: parseOptions(e.target.value) })} />}
              {c.type === "menu" && <textarea rows={3} aria-label="Itens (id: rótulo)" placeholder="id: rótulo, um por linha" value={optionsText(c.items)} onChange={(e) => setComp(si, ci, { items: parseOptions(e.target.value).map((o) => ({ ...o, on_click: (c.items ?? []).find((i: Q) => i.id === o.id)?.on_click ?? [] })) })} />}
              {c.type === "table" && (
                <textarea rows={4} aria-label="Tabela" placeholder="primeira linha: colunas | demais: id: célula | célula" value={[(c.columns ?? []).join(" | "), ...(c.rows ?? []).map((r: Q) => `${r.id}: ${(r.cells ?? []).join(" | ")}`)].join("\n")}
                  onChange={(e) => { const [head = "", ...rest] = lines(e.target.value); setComp(si, ci, { columns: head.split("|").map((x) => x.trim()), rows: rest.map((l) => { const [id, ...cells] = l.split(":"); return { id: id!.trim(), cells: cells.join(":").split("|").map((x) => x.trim()) }; }) }); }} />
              )}
              {c.type === "button" && <ActionsEditor actions={c.on_click ?? []} vars={vars} screens={screenIds} onChange={(a) => setComp(si, ci, { on_click: a })} />}
              {["input", "select", "checkbox", "radio_group", "tabs", "table", "toggle"].includes(c.type) && <ActionsEditor actions={c.on_change ?? []} vars={vars} screens={screenIds} onChange={(a) => setComp(si, ci, { on_change: a })} />}
              <ConditionBuilder label="Visível quando" expr={c.visible_if} vars={vars} onChange={(e) => setComp(si, ci, { visible_if: e })} />
              <ConditionBuilder label="Habilitado quando" expr={c.enabled_if} vars={vars} onChange={(e) => setComp(si, ci, { enabled_if: e })} />
            </div>
          ))}
          <Button variant="ghost" onClick={() => setScreen({ screens: screen.screens.map((x: Q, i: number) => (i === si ? { ...x, components: [...x.components, { id: nextId(screen.screens.flatMap((t: Q) => t.components.map((k: Q) => k.id)), "comp"), type: "text", text: "Novo texto" }] } : x)) })}>+ Componente</Button>
        </section>
      ))}
      <Button variant="ghost" onClick={() => setScreen({ screens: [...screen.screens, { id: nextId(screenIds, "tela"), title: "Nova tela", components: [] }] })}>+ Tela</Button>

      <section className="subpanel">
        <h4>Verificações (como a questão é corrigida)</h4>
        <p className="muted">A questão é concluída quando todas as verificações são satisfeitas. Elas não aparecem para quem faz a prova.</p>
        {checks.map((c, i) => (
          <div key={c.id} className="component-card">
            <div className="cond-row">
              <input value={c.label ?? ""} aria-label="Descrição da verificação" onChange={(e) => setChecks(checks.map((x, k) => (k === i ? { ...x, label: e.target.value } : x)))} />
              <input type="number" min={1} max={100} value={c.points ?? 1} aria-label="Pontos" onChange={(e) => setChecks(checks.map((x, k) => (k === i ? { ...x, points: Number(e.target.value) } : x)))} />
              <Button variant="ghost" aria-label="Remover verificação" onClick={() => setChecks(checks.filter((_, k) => k !== i))}>✕</Button>
            </div>
            <ConditionBuilder label="Satisfeita quando" expr={c.when} vars={vars} onChange={(e) => setChecks(checks.map((x, k) => (k === i ? { ...x, when: e ?? { "==": [1, 1] } } : x)))} />
          </div>
        ))}
        <Button variant="ghost" disabled={vars.length === 0} onClick={() => setChecks([...checks, { id: nextId(checks.map((c) => c.id), "v"), label: "Nova verificação", when: { "==": [{ var: vars[0] }, true] }, points: 1 }])}>+ Verificação</Button>
      </section>

      {q.type === "active_screen" && (
        <section className="subpanel">
          <label className="field">Fidelidade à interface original
            <select value={q.fidelity} onChange={(e) => set({ fidelity: e.target.value })}>
              <option value="reconstructed">Reconstruída</option><option value="approximate">Aproximada</option><option value="screenshot_only">Somente captura de tela</option>
            </select>
          </label>
          <label className="field">Limitações (uma por linha; aparecem para o usuário)
            <textarea rows={3} value={(q.limitations ?? []).join("\n")} onChange={(e) => set({ limitations: lines(e.target.value) })} />
          </label>
        </section>
      )}
    </div>
  );
}

export { BlocksEditor };
