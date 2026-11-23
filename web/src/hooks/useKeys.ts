import { useEffect, useRef } from "react";

/** Atalhos de teclado; ignora quando o foco está em campos de texto. */
export function useKeys(handlers: Record<string, () => void>, enabled = true): void {
  const ref = useRef(handlers);
  ref.current = handlers;
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) && target.getAttribute("type") !== "checkbox" && target.getAttribute("type") !== "radio") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const fn = ref.current[e.key.toLowerCase()];
      if (fn) {
        e.preventDefault();
        fn();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled]);
}
