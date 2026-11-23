import { useState } from "react";
import { api } from "../api/client";
import type { CaseStudy, ImageRef } from "../api/types";
import { Badge, Button, Modal } from "./ui";

/** HTML já sanitizado pelo servidor. */
export function Html({ html, className = "" }: { html: string; className?: string }) {
  return <div className={`rich ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}

/** Imagens da questão. Cada uma abre ampliada, com zoom. Anexos ausentes são sinalizados. */
export function Exhibits({ images, label = "Exhibit" }: { images: ImageRef[]; label?: string }) {
  const [open, setOpen] = useState<ImageRef | null>(null);
  const [zoom, setZoom] = useState(1);
  if (images.length === 0) return null;
  return (
    <div className="exhibits">
      {images.map((img, i) =>
        img.sha ? (
          <button key={img.sha + i} className="exhibit" onClick={() => { setZoom(1); setOpen(img); }}>
            <img src={api.assetUrl(img.sha)} alt={`${label} ${i + 1}`} loading="lazy" />
            <span>{label} {images.length > 1 ? i + 1 : ""}</span>
          </button>
        ) : (
          <Badge key={img.name + i} tone="warn">Anexo ausente: {img.name}</Badge>
        ),
      )}
      {open?.sha && (
        <Modal title={label} onClose={() => setOpen(null)} wide>
          <div className="zoom-bar">
            <Button onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))} aria-label="Diminuir">−</Button>
            <span>{Math.round(zoom * 100)}%</span>
            <Button onClick={() => setZoom((z) => Math.min(4, z + 0.25))} aria-label="Aumentar">+</Button>
            <Button variant="ghost" onClick={() => setZoom(1)}>100%</Button>
          </div>
          <div className="zoom-area">
            <img src={api.assetUrl(open.sha)} alt={label} style={{ width: `${zoom * 100}%`, maxWidth: "none" }} />
          </div>
        </Modal>
      )}
    </div>
  );
}

export function CasePanel({ study, defaultOpen = true }: { study: CaseStudy; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <aside className="case-panel" aria-label="Estudo de caso">
      <button className="case-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        {study.title} {open ? "▾" : "▸"}
      </button>
      {open && <Html html={study.text} />}
    </aside>
  );
}
