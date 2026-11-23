import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface ToastItem {
  id: number;
  text: string;
  tone: "good" | "bad" | "info";
  action?: { label: string; run: () => void };
}
interface ToastApi {
  show: (text: string, opts?: { tone?: ToastItem["tone"]; action?: ToastItem["action"]; ms?: number }) => void;
}

const Ctx = createContext<ToastApi>({ show: () => undefined });
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = (id: number) => setItems((all) => all.filter((t) => t.id !== id));
  const show = useCallback<ToastApi["show"]>((text, opts = {}) => {
    const id = Date.now() + Math.random();
    setItems((all) => [...all, { id, text, tone: opts.tone ?? "info", action: opts.action }]);
    window.setTimeout(() => dismiss(id), opts.ms ?? 8000);
  }, []);
  return (
    <Ctx.Provider value={{ show }}>
      {children}
      <div className="toasts" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}`}>
            <span>{t.text}</span>
            {t.action && (
              <button className="link" onClick={() => { t.action?.run(); dismiss(t.id); }}>{t.action.label}</button>
            )}
            <button className="icon-btn" aria-label="Dispensar" onClick={() => dismiss(t.id)}>×</button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
