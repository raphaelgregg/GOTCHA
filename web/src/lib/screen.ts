/** Motor declarativo do Active Screen: porta fiel do servidor, verificada pelos mesmos vetores. */
import { evaluate, LogicError, validate } from "./logic";

export type VarType = "string" | "number" | "bool" | "list";
export interface Action { do: "set" | "toggle" | "goto" | "message" | "append"; var?: string | null; value?: unknown; screen?: string | null; text?: string | null }
export interface Option { id: string; label?: string }
export interface MenuItem { id: string; label?: string; on_click?: Action[] }
export interface Row { id: string; cells?: string[] }
export type ComponentType = "text" | "image" | "button" | "input" | "select" | "checkbox" | "radio_group" | "tabs" | "menu" | "table" | "toggle";
export interface Component {
  id: string; type: ComponentType; label?: string; text?: string; asset?: string | null; bind?: string | null;
  options?: Option[]; items?: MenuItem[]; columns?: string[]; rows?: Row[];
  visible_if?: unknown; enabled_if?: unknown; on_click?: Action[]; on_change?: Action[];
}
export interface Screen { id: string; title?: string; components: Component[] }
export interface ScreenSpec { screens: Screen[]; state: Record<string, { type: VarType; initial?: unknown }>; start: string }
export interface ScreenEvent { component: string; type: "click" | "change"; value?: unknown }
export interface Run { state: Record<string, unknown>; screen: string; messages: string[]; applied: number; ignored: number }

export const MAX_EVENTS = 1000;
const MAX_ACTIONS = 50;
const MAX_TEXT = 500;
const DEFAULTS: Record<VarType, unknown> = { string: "", number: 0, bool: false, list: [] };

export function initialRun(spec: ScreenSpec): Run {
  const state: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(spec.state)) state[k] = structuredClone(v.initial ?? DEFAULTS[v.type]);
  return { state, screen: spec.start, messages: [], applied: 0, ignored: 0 };
}

const accepts = (type: VarType, v: unknown): boolean =>
  type === "string" ? typeof v === "string" && v.length <= MAX_TEXT : type === "number" ? typeof v === "number" : type === "bool" ? typeof v === "boolean" : Array.isArray(v);

function truthy(expr: unknown, state: Record<string, unknown>): boolean {
  return expr === undefined || expr === null ? true : Boolean(evaluate(expr, state));
}

function changeValue(c: Component, v: unknown, spec: ScreenSpec): boolean {
  if (["select", "radio_group", "tabs"].includes(c.type)) return typeof v === "string" && (c.options ?? []).some((o) => o.id === v);
  if (c.type === "table") return typeof v === "string" && (c.rows ?? []).some((r) => r.id === v);
  if (c.type === "checkbox" || c.type === "toggle") return typeof v === "boolean";
  if (c.type === "input" && c.bind && spec.state[c.bind]) return accepts(spec.state[c.bind]!.type, v);
  return false;
}

function applyActions(actions: Action[], spec: ScreenSpec, run: Run): void {
  for (const a of actions.slice(0, MAX_ACTIONS)) {
    if (a.do === "goto" && spec.screens.some((s) => s.id === a.screen)) run.screen = a.screen!;
    else if (a.do === "message" && a.text) run.messages.push(a.text.slice(0, MAX_TEXT));
    else if (a.var && spec.state[a.var]) {
      const t = spec.state[a.var]!.type;
      if (a.do === "set" && accepts(t, a.value)) run.state[a.var] = structuredClone(a.value);
      else if (a.do === "toggle" && t === "bool") run.state[a.var] = !run.state[a.var];
      else if (a.do === "append" && t === "list" && (run.state[a.var] as unknown[]).length < 1000) (run.state[a.var] as unknown[]).push(structuredClone(a.value));
    }
  }
}

/** Aplica um evento ao estado (altera `run`). Devolve false se o evento foi ignorado. */
export function applyEvent(spec: ScreenSpec, run: Run, ev: ScreenEvent): boolean {
  const comp = spec.screens.find((s) => s.id === run.screen)?.components.find((c) => c.id === ev.component);
  if (!comp) return false;
  try {
    if (!(truthy(comp.visible_if, run.state) && truthy(comp.enabled_if, run.state))) return false;
  } catch (e) {
    if (e instanceof LogicError) return false;
    throw e;
  }
  if (ev.type === "change") {
    if (!changeValue(comp, ev.value, spec) || !comp.bind || !spec.state[comp.bind]) return false;
    run.state[comp.bind] = ev.value;
    applyActions(comp.on_change ?? [], spec, run);
    return true;
  }
  if (ev.type === "click") {
    if (comp.type === "button") return applyActions(comp.on_click ?? [], spec, run), true;
    if (comp.type === "menu") {
      const item = (comp.items ?? []).find((i) => i.id === ev.value);
      return item ? (applyActions(item.on_click ?? [], spec, run), true) : false;
    }
  }
  return false;
}

export function replay(spec: ScreenSpec, events: ScreenEvent[]): Run {
  const run = initialRun(spec);
  events.forEach((ev, i) => {
    if (i >= MAX_EVENTS) {
      if (i === MAX_EVENTS) run.ignored += events.length - MAX_EVENTS;
      return;
    }
    if (applyEvent(spec, run, ev)) run.applied += 1;
    else run.ignored += 1;
  });
  return run;
}

export function validateScreen(spec: ScreenSpec): string[] {
  const errors: string[] = [];
  const ids = spec.screens.map((s) => s.id);
  if (new Set(ids).size !== ids.length) errors.push("Há telas com identificador repetido.");
  if (!ids.includes(spec.start)) errors.push(`A tela inicial ${spec.start} não existe.`);
  const comps = spec.screens.flatMap((s) => s.components);
  if (new Set(comps.map((c) => c.id)).size !== comps.length) errors.push("Há componentes com identificador repetido.");
  const checkActions = (where: string, actions: Action[]) => {
    for (const a of actions) {
      if (["set", "toggle", "append"].includes(a.do) && !(a.var && spec.state[a.var])) errors.push(`${where}: a variável ${a.var} não existe.`);
      if (a.do === "goto" && !ids.includes(a.screen ?? "")) errors.push(`${where}: a tela ${a.screen} não existe.`);
      if (a.do === "message" && !a.text) errors.push(`${where}: \`message\` exige texto.`);
    }
  };
  for (const c of comps) {
    if (c.bind && !spec.state[c.bind]) errors.push(`componente ${c.id}: a variável ${c.bind} não existe.`);
    for (const [label, expr] of [["visible_if", c.visible_if], ["enabled_if", c.enabled_if]] as const) {
      if (expr == null) continue;
      try { validate(expr); } catch (e) { errors.push(`componente ${c.id} (${label}): ${(e as Error).message}`); }
    }
    checkActions(`componente ${c.id}`, [...(c.on_click ?? []), ...(c.on_change ?? [])]);
    for (const item of c.items ?? []) checkActions(`componente ${c.id}/${item.id}`, item.on_click ?? []);
  }
  return errors;
}
