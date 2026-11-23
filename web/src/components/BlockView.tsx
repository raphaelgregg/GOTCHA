import { useState } from "react";
import { api } from "../api/client";
import type { Block, ImageBlock } from "../api/question";
import { Badge, Button, Modal } from "./ui";

/** Imagem do enunciado, alternativa ou resposta. Abre ampliada, com zoom; anexo ausente é sinalizado. */
export function ImageView({ block }: { block: ImageBlock }) {
  const [open, setOpen] = useState(false);
  const [zoom, setZoom] = useState(1);
  if (!block.asset) return <Badge tone="warn">Anexo ausente{block.name ? `: ${block.name}` : ""}</Badge>;
  const url = api.assetUrl(block.asset);
  return (
    <figure className={`block-image align-${block.align}`} style={{ width: `${block.width_pct}%` }}>
      <button className="image-btn" onClick={() => { setZoom(1); setOpen(true); }} aria-label={`Ampliar: ${block.alt || block.name || "imagem"}`}>
        <img src={url} alt={block.alt} loading="lazy" />
      </button>
      {block.caption && <figcaption>{block.caption}</figcaption>}
      {open && (
        <Modal title={block.alt || "Imagem"} onClose={() => setOpen(false)} wide>
          <div className="zoom-bar">
            <Button onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))} aria-label="Diminuir">−</Button>
            <span>{Math.round(zoom * 100)}%</span>
            <Button onClick={() => setZoom((z) => Math.min(4, z + 0.25))} aria-label="Aumentar">+</Button>
            <Button variant="ghost" onClick={() => setZoom(1)}>100%</Button>
          </div>
          <div className="zoom-area"><img src={url} alt={block.alt} style={{ width: `${zoom * 100}%`, maxWidth: "none" }} /></div>
        </Modal>
      )}
    </figure>
  );
}

/** Renderiza a lista de blocos na ordem. HTML já vem sanitizado do servidor; o resto é texto. */
export function BlockView({ blocks, inline }: { blocks: Block[]; inline?: boolean }) {
  return (
    <div className={`blocks ${inline ? "inline" : ""}`}>
      {blocks.map((b, i) => {
        switch (b.type) {
          case "paragraph": return <p key={i}>{b.text}</p>;
          case "html": return <div key={i} className="rich" dangerouslySetInnerHTML={{ __html: b.html }} />;
          case "table":
            return (
              <div key={i} className="rich">
                <table><tbody>
                  {b.rows.map((row, r) => <tr key={r}>{row.map((cell, c) => (b.header && r === 0 ? <th key={c}>{cell}</th> : <td key={c}>{cell}</td>))}</tr>)}
                </tbody></table>
              </div>
            );
          case "code": return <pre key={i} className="code"><code>{b.code}</code></pre>;
          case "image": return <ImageView key={i} block={b} />;
          case "attachment":
            return b.asset ? <a key={i} className="btn btn-secondary" href={api.assetUrl(b.asset)} download>📎 {b.label || "Anexo"}</a> : <Badge key={i} tone="warn">Anexo ausente</Badge>;
        }
      })}
    </div>
  );
}

/** Estudo de caso: contexto compartilhado, com uma aba por seção. */
export function CaseDocPanel({ study, defaultOpen = true }: { study: import("../api/types").CaseDoc; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const [tab, setTab] = useState(0);
  const section = study.sections[Math.min(tab, study.sections.length - 1)];
  return (
    <aside className="case-panel" aria-label="Estudo de caso">
      <button className="case-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>{study.title} {open ? "▾" : "▸"}</button>
      {open && study.sections.length > 1 && (
        <div className="seg" role="tablist">
          {study.sections.map((s, i) => <button key={s.id} role="tab" aria-selected={tab === i} className={tab === i ? "is-on" : ""} onClick={() => setTab(i)}>{s.title || `Seção ${i + 1}`}</button>)}
        </div>
      )}
      {open && section && <BlockView blocks={section.blocks} />}
    </aside>
  );
}
