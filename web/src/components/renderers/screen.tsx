import { useMemo } from "react";
import { api } from "../../api/client";
import { evaluate } from "../../lib/logic";
import { applyEvent, replay, type Component, type Run, type ScreenEvent, type ScreenSpec } from "../../lib/screen";
import { Button, Notice } from "../ui";
import type { Of, RendererProps } from "./types";

function visibleAndEnabled(c: Component, run: Run): [boolean, boolean] {
  try {
    const vis = c.visible_if == null || Boolean(evaluate(c.visible_if, run.state));
    const en = c.enabled_if == null || Boolean(evaluate(c.enabled_if, run.state));
    return [vis, en];
  } catch {
    return [false, false];
  }
}

/** Reproduz uma tela declarativa. Só componentes controlados; nada importado é executado. */
export function ScreenPlayer({ spec, events, onEvents, locked }: { spec: ScreenSpec; events: ScreenEvent[]; onEvents: (e: ScreenEvent[]) => void; locked?: boolean }) {
  const run = useMemo(() => replay(spec, events), [spec, events]);
  const screen = spec.screens.find((s) => s.id === run.screen) ?? spec.screens[0]!;

  const send = (ev: ScreenEvent) => {
    if (locked) return;
    const probe: Run = structuredClone(run);
    if (applyEvent(spec, probe, ev)) onEvents([...events, ev]); // eventos inválidos nem entram no registro
  };

  return (
    <div className="screen-player" role="group" aria-label={screen.title || "Tela simulada"}>
      {screen.title && <h4 className="screen-title">{screen.title}</h4>}
      {screen.components.map((c) => {
        const [visible, enabled] = visibleAndEnabled(c, run);
        if (!visible) return null;
        const off = !enabled || locked;
        const value = c.bind ? run.state[c.bind] : undefined;
        const label = c.label ? <label className="screen-label" htmlFor={`sc-${c.id}`}>{c.label}</label> : null;
        switch (c.type) {
          case "text": return <p key={c.id}>{c.text || c.label}</p>;
          case "image": return c.asset ? <img key={c.id} src={api.assetUrl(c.asset)} alt={c.label || ""} className="screen-img" /> : null;
          case "button": return <Button key={c.id} variant="primary" disabled={off} onClick={() => send({ component: c.id, type: "click" })}>{c.label || "OK"}</Button>;
          case "input":
            return (
              <div key={c.id} className="screen-field">{label}
                <input id={`sc-${c.id}`} value={String(value ?? "")} disabled={off} maxLength={500}
                  onChange={(e) => send({ component: c.id, type: "change", value: typeof value === "number" ? Number(e.target.value) : e.target.value })} />
              </div>
            );
          case "select":
            return (
              <div key={c.id} className="screen-field">{label}
                <select id={`sc-${c.id}`} value={String(value ?? "")} disabled={off} onChange={(e) => send({ component: c.id, type: "change", value: e.target.value })}>
                  {!(c.options ?? []).some((o) => o.id === value) && <option value="">Selecione…</option>}
                  {(c.options ?? []).map((o) => <option key={o.id} value={o.id}>{o.label || o.id}</option>)}
                </select>
              </div>
            );
          case "checkbox":
          case "toggle":
            return (
              <label key={c.id} className="check"><input type="checkbox" role={c.type === "toggle" ? "switch" : undefined} checked={Boolean(value)} disabled={off}
                onChange={(e) => send({ component: c.id, type: "change", value: e.target.checked })} /> {c.label}</label>
            );
          case "radio_group":
            return (
              <fieldset key={c.id} disabled={off} className="screen-field"><legend>{c.label}</legend>
                {(c.options ?? []).map((o) => (
                  <label key={o.id} className="check"><input type="radio" name={`sc-${c.id}`} checked={value === o.id} onChange={() => send({ component: c.id, type: "change", value: o.id })} /> {o.label || o.id}</label>
                ))}
              </fieldset>
            );
          case "tabs":
            return (
              <div key={c.id} className="seg" role="tablist" aria-label={c.label}>
                {(c.options ?? []).map((o) => (
                  <button key={o.id} role="tab" aria-selected={value === o.id} className={value === o.id ? "is-on" : ""} disabled={off}
                    onClick={() => send({ component: c.id, type: "change", value: o.id })}>{o.label || o.id}</button>
                ))}
              </div>
            );
          case "menu":
            return (
              <ul key={c.id} className="screen-menu" role="menu" aria-label={c.label}>
                {(c.items ?? []).map((i) => <li key={i.id} role="none"><button role="menuitem" disabled={off} onClick={() => send({ component: c.id, type: "click", value: i.id })}>{i.label || i.id}</button></li>)}
              </ul>
            );
          case "table":
            return (
              <table key={c.id} className="screen-table">
                <thead><tr>{(c.columns ?? []).map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
                <tbody>
                  {(c.rows ?? []).map((r) => (
                    <tr key={r.id} className={value === r.id ? "is-on" : ""} tabIndex={off ? -1 : 0} aria-selected={value === r.id}
                      onClick={() => !off && send({ component: c.id, type: "change", value: r.id })}
                      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), !off && send({ component: c.id, type: "change", value: r.id }))}>
                      {(r.cells ?? []).map((cell, i) => <td key={i}>{cell}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            );
        }
      })}
      {run.messages.slice(-2).map((m, i) => <Notice key={i}>{m}</Notice>)}
      {!locked && events.length > 0 && <Button variant="ghost" onClick={() => onEvents([])}>Reiniciar tela</Button>}
    </div>
  );
}

const FIDELITY = { reconstructed: "Reconstruída", approximate: "Aproximada", screenshot_only: "Somente captura de tela" } as const;

export function ActiveScreenRenderer({ q, value, onChange, locked }: RendererProps<Of<"active_screen">>) {
  return (
    <div className="active-screen">
      <Notice tone="warn">
        <strong>Fidelidade: {FIDELITY[q.fidelity]}.</strong> Esta é uma reprodução simplificada, não a interface original.
        {q.limitations.length > 0 && <ul>{q.limitations.map((l) => <li key={l}>{l}</li>)}</ul>}
      </Notice>
      <ScreenPlayer spec={q.screen} events={value?.events ?? []} locked={locked} onEvents={(events) => onChange({ ...value, events })} />
    </div>
  );
}
