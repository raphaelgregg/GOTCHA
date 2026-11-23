/** Condições declarativas com a sintaxe do JSON Logic (subconjunto fechado, igual ao do servidor). */
export class LogicError extends Error {}

const MAX_DEPTH = 12;
const MAX_NODES = 300;
const BINARY = new Set(["==", "!=", "<", "<=", ">", ">=", "in"]);
const OPERATORS = new Set(["var", "!", "and", "or", ...BINARY]);

type Json = unknown;
const asArgs = (v: Json): Json[] => (Array.isArray(v) ? v : [v]);

export function validate(expr: Json): void {
  let count = 0;
  const walk = (node: Json, depth: number): void => {
    if (++count > MAX_NODES) throw new LogicError("Expressão acima do tamanho máximo permitido.");
    if (depth > MAX_DEPTH) throw new LogicError("Expressão muito profunda.");
    if (Array.isArray(node)) return node.forEach((n) => walk(n, depth + 1));
    if (node === null || ["string", "number", "boolean"].includes(typeof node)) return;
    if (typeof node !== "object") throw new LogicError("Valor não permitido na expressão.");
    const entries = Object.entries(node as Record<string, Json>);
    if (entries.length !== 1) throw new LogicError("Cada operador deve ter exatamente uma chave.");
    const [op, raw] = entries[0]!;
    if (!OPERATORS.has(op)) throw new LogicError(`Operador desconhecido: ${op}.`);
    const args = asArgs(raw);
    if (op === "var") {
      if (args.length < 1 || args.length > 2 || typeof args[0] !== "string") throw new LogicError("`var` exige o nome da variável.");
    } else if (BINARY.has(op) && args.length !== 2) throw new LogicError(`\`${op}\` exige dois argumentos.`);
    else if (op === "!" && args.length !== 1) throw new LogicError("`!` exige um argumento.");
    else if ((op === "and" || op === "or") && args.length === 0) throw new LogicError(`\`${op}\` exige argumentos.`);
    args.forEach((a) => walk(a, depth + 1));
  };
  walk(expr, 0);
}

const lookup = (path: string, data: Record<string, Json>): Json => {
  let cur: Json = data;
  for (const part of path.split(".")) {
    if (cur && typeof cur === "object" && !Array.isArray(cur) && part in (cur as object)) cur = (cur as Record<string, Json>)[part];
    else return null;
  }
  return cur ?? null;
};

const strictEq = (a: Json, b: Json): boolean => {
  if ((typeof a === "boolean") !== (typeof b === "boolean")) return false;
  return JSON.stringify(a) === JSON.stringify(b);
};
const isNum = (v: Json): v is number => typeof v === "number";

export function evaluate(expr: Json, data: Record<string, Json>): Json {
  validate(expr);
  return run(expr, data);
}

function run(node: Json, data: Record<string, Json>): Json {
  if (Array.isArray(node)) return node.map((n) => run(n, data));
  if (node === null || typeof node !== "object") return node;
  const [op, raw] = Object.entries(node as Record<string, Json>)[0]!;
  const args = asArgs(raw);
  if (op === "var") {
    const found = lookup(args[0] as string, data);
    return found !== null || args.length === 1 ? found : run(args[1], data);
  }
  if (op === "and") {
    let r: Json = true;
    for (const a of args) {
      r = run(a, data);
      if (!r) return r;
    }
    return r;
  }
  if (op === "or") {
    let r: Json = false;
    for (const a of args) {
      r = run(a, data);
      if (r) return r;
    }
    return r;
  }
  const [a, b] = args.map((x) => run(x, data));
  if (op === "!") return !a;
  if (op === "==") return strictEq(a, b);
  if (op === "!=") return !strictEq(a, b);
  if (op === "in") return Array.isArray(b) ? b.some((x) => strictEq(x, a)) : typeof b === "string" && typeof a === "string" && b.includes(a);
  if (!((isNum(a) && isNum(b)) || (typeof a === "string" && typeof b === "string"))) return false;
  const [x, y] = [a as number, b as number];
  return op === "<" ? x < y : op === "<=" ? x <= y : op === ">" ? x > y : x >= y;
}
