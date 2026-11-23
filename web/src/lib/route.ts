export type RouteName = "library" | "batch" | "simulado" | "exam" | "result" | "history";
export interface Route {
  name: RouteName;
  id: string | null;
  query: Record<string, string>;
}

const NAMES = new Set<string>(["batch", "simulado", "exam", "result", "history"]);

export function parseHash(hash: string): Route {
  const [path = "", search = ""] = hash.replace(/^#\/?/, "").split("?");
  const [first = "", id = ""] = path.split("/");
  const query = Object.fromEntries(new URLSearchParams(search));
  const name = (NAMES.has(first) ? first : "library") as RouteName;
  return { name, id: id || null, query };
}

export function buildHash(name: RouteName, id?: string, query?: Record<string, string>): string {
  const base = name === "library" ? "#/" : `#/${name}${id ? `/${id}` : ""}`;
  const qs = query ? new URLSearchParams(query).toString() : "";
  return qs ? `${base}?${qs}` : base;
}

export function navigate(name: RouteName, id?: string, query?: Record<string, string>): void {
  window.location.hash = buildHash(name, id, query);
}
