import { useRef, useState } from "react";
import { api } from "../api/client";
import type { ImportResult } from "../api/types";
import { messageOf } from "../hooks/useAsync";
import { plural } from "../lib/format";
import { Badge, Button, Notice } from "./ui";

const ACCEPT = ".html,.htm,.txt,.pdf,.json,.csv,.xlsx,.zip,.vce";

export function ImportDropzone({ onImported }: { onImported: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<ImportResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function send(files: File[]) {
    if (files.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const { results } = await api.importFiles(files);
      setResults(results);
      if (results.some((r) => r.ok)) onImported();
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div className="import">
      <div
        className={`dropzone ${over ? "is-over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); void send(Array.from(e.dataTransfer.files)); }}
      >
        <p><strong>Arraste os arquivos aqui</strong> ou escolha no computador.</p>
        <p className="muted">HTML salvo, TXT, PDF, CSV/XLSX, JSON do app e ZIP (página + pasta de imagens). Vários de uma vez.</p>
        <input ref={input} type="file" multiple accept={ACCEPT} hidden onChange={(e) => void send(Array.from(e.target.files ?? []))} />
        <Button variant="primary" busy={busy} onClick={() => input.current?.click()}>Escolher arquivos</Button>
      </div>
      {error && <Notice tone="bad">{error}</Notice>}
      {results.length > 0 && (
        <ul className="import-results">
          {results.map((r, i) => (
            <li key={r.filename + i} className={r.ok ? "ok" : "fail"}>
              <span className="name">{r.filename}</span>
              {r.ok ? (
                <>
                  <Badge tone="good">{r.format?.toUpperCase()} · {plural(r.count ?? 0, "questão", "questões")}</Badge>
                  {!!r.warning_count && <Badge tone="warn">{plural(r.warning_count, "aviso", "avisos")}</Badge>}
                  <span className="muted">pronto para revisar abaixo</span>
                </>
              ) : (
                <span className="error-text">{r.error}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
