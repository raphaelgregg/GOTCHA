import { useEffect, useState } from "react";
import { api, type AssetInfo } from "../../api/client";
import type { Block, ImageBlock } from "../../api/question";
import { Badge, Button } from "../ui";
import { move, para } from "./util";

const NEW: Record<string, () => Block> = {
  paragraph: () => para(""),
  image: () => ({ type: "image", asset: null, name: "", alt: "", width_pct: 100, align: "center", caption: "" }),
  table: () => ({ type: "table", rows: [["Coluna 1", "Coluna 2"], ["", ""]], header: true }),
  code: () => ({ type: "code", code: "", language: "" }),
  attachment: () => ({ type: "attachment", asset: null, label: "" }),
};
const LABEL: Record<string, string> = { paragraph: "Texto", image: "Imagem", table: "Tabela", code: "Código", attachment: "Anexo", html: "HTML" };

export function ImageEditor({ block, onChange }: { block: ImageBlock; onChange: (b: ImageBlock) => void }) {
  const [info, setInfo] = useState<AssetInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setInfo(null);
    if (block.asset) api.assetInfo(block.asset).then(setInfo).catch(() => setInfo(null));
  }, [block.asset]);

  async function pick(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const a = await api.uploadAsset(file);
      onChange({ ...block, asset: a.id, name: file.name, alt: block.alt || a.default_alt });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao enviar a imagem.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="image-editor">
      <div className="image-thumb">
        {block.asset ? <img src={api.assetUrl(block.asset)} alt={block.alt} /> : <Badge tone="warn">Anexo ausente{block.name ? `: ${block.name}` : ""}</Badge>}
      </div>
      <div className="stack-sm">
        <label className="btn btn-secondary file-btn">
          {busy ? "Enviando…" : block.asset ? "Substituir imagem" : "Escolher imagem"}
          <input type="file" accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml" hidden onChange={(e) => void pick(e.target.files?.[0])} />
        </label>
        {block.asset && <Button variant="ghost" onClick={() => onChange({ ...block, asset: null })}>Remover imagem (manter o espaço)</Button>}
        {info && <span className="muted">{info.mime} · {info.width}×{info.height}px · {(info.size / 1024).toFixed(0)} KB</span>}
        {error && <span className="error-text">{error}</span>}
        <label className="field">Descrição alternativa<input value={block.alt} onChange={(e) => onChange({ ...block, alt: e.target.value })} /></label>
        <div className="grid-3">
          <label className="field">Largura ({block.width_pct}%)<input type="range" min={10} max={100} step={5} value={block.width_pct} onChange={(e) => onChange({ ...block, width_pct: Number(e.target.value) })} /></label>
          <label className="field">Alinhamento
            <select value={block.align} onChange={(e) => onChange({ ...block, align: e.target.value as ImageBlock["align"] })}>
              <option value="left">Esquerda</option><option value="center">Centro</option><option value="right">Direita</option>
            </select>
          </label>
          <label className="field">Legenda<input value={block.caption} onChange={(e) => onChange({ ...block, caption: e.target.value })} /></label>
        </div>
      </div>
    </div>
  );
}

function BlockRow({ block, onChange }: { block: Block; onChange: (b: Block) => void }) {
  switch (block.type) {
    case "paragraph": return <textarea rows={2} value={block.text} onChange={(e) => onChange({ ...block, text: e.target.value })} aria-label="Texto" />;
    case "html": return <textarea rows={3} className="mono" value={block.html} onChange={(e) => onChange({ ...block, html: e.target.value })} aria-label="HTML (sanitizado ao salvar)" />;
    case "table":
      return (
        <div className="stack-sm">
          <textarea rows={4} className="mono" aria-label="Linhas da tabela (células separadas por |)" value={block.rows.map((r) => r.join(" | ")).join("\n")}
            onChange={(e) => onChange({ ...block, rows: e.target.value.split("\n").map((l) => l.split("|").map((c) => c.trim())) })} />
          <label className="check"><input type="checkbox" checked={block.header} onChange={(e) => onChange({ ...block, header: e.target.checked })} /> Primeira linha é cabeçalho</label>
        </div>
      );
    case "code":
      return (
        <div className="stack-sm">
          <input value={block.language} placeholder="linguagem (opcional)" onChange={(e) => onChange({ ...block, language: e.target.value })} aria-label="Linguagem" />
          <textarea rows={4} className="mono" value={block.code} onChange={(e) => onChange({ ...block, code: e.target.value })} aria-label="Código" />
        </div>
      );
    case "image": return <ImageEditor block={block} onChange={onChange} />;
    case "attachment":
      return (
        <div className="stack-sm">
          <input value={block.label} placeholder="Rótulo do anexo" onChange={(e) => onChange({ ...block, label: e.target.value })} aria-label="Rótulo" />
          <label className="btn btn-secondary file-btn">{block.asset ? "Substituir arquivo" : "Escolher arquivo"}
            <input type="file" hidden onChange={async (e) => { const f = e.target.files?.[0]; if (f) { const a = await api.uploadAsset(f); onChange({ ...block, asset: a.id, label: block.label || f.name }); } }} />
          </label>
        </div>
      );
  }
}

/** Editor de blocos: texto, imagem, tabela, código e anexo, com reposicionamento. */
export function BlocksEditor({ blocks, onChange, label, compact, allow }: { blocks: Block[]; onChange: (b: Block[]) => void; label?: string; compact?: boolean; allow?: string[] }) {
  const kinds = allow ?? Object.keys(NEW);
  return (
    <div className={`blocks-editor ${compact ? "compact" : ""}`}>
      {label && <h4>{label}</h4>}
      {blocks.map((b, i) => (
        <div key={i} className="block-row">
          <div className="block-tools">
            <Badge>{LABEL[b.type]}</Badge>
            <Button variant="ghost" onClick={() => onChange(move(blocks, i, i - 1))} disabled={i === 0} aria-label="Mover para cima">↑</Button>
            <Button variant="ghost" onClick={() => onChange(move(blocks, i, i + 1))} disabled={i === blocks.length - 1} aria-label="Mover para baixo">↓</Button>
            <Button variant="ghost" onClick={() => onChange(blocks.filter((_, k) => k !== i))} aria-label="Remover bloco">✕</Button>
          </div>
          <BlockRow block={b} onChange={(nb) => onChange(blocks.map((x, k) => (k === i ? nb : x)))} />
        </div>
      ))}
      <div className="actions">
        {kinds.map((k) => <Button key={k} variant="ghost" onClick={() => onChange([...blocks, NEW[k]!()])}>+ {LABEL[k]}</Button>)}
      </div>
    </div>
  );
}
