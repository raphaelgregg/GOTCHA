import { DndContext, KeyboardSensor, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { useState } from "react";
import type { DragItem } from "../../api/question";
import { BlockView, ImageView } from "../BlockView";
import { Button } from "../ui";
import type { Of, RendererProps } from "./types";

function Chip({ item, disabled, selected, onPick }: { item: DragItem; disabled?: boolean; selected?: boolean; onPick: () => void }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: item.id, disabled });
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined;
  return (
    <button ref={setNodeRef} style={style} {...attributes} {...listeners} onClick={onPick} disabled={disabled}
      className={`chip-item ${selected ? "is-selected" : ""} ${isDragging ? "is-dragging" : ""}`} aria-pressed={selected}>
      <BlockView blocks={item.blocks} inline />
    </button>
  );
}

function Zone({ id, children, full }: { id: string; children: React.ReactNode; full: boolean }) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return <div ref={setNodeRef} className={`dropzone-target ${isOver ? "is-over" : ""} ${full ? "is-full" : ""}`}>{children}</div>;
}

export function DragDropRenderer({ q, value, onChange, locked, solution }: RendererProps<Of<"drag_drop">>) {
  const placements = value?.placements ?? {};
  const [picked, setPicked] = useState<string | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }), useSensor(KeyboardSensor));
  const items = new Map(q.items.map((i) => [i.id, i]));
  const key = solution?.key?.placements as Record<string, string[]> | undefined;
  const used = new Set(Object.values(placements).flat());

  const place = (itemId: string, targetId: string) => {
    const target = q.targets.find((t) => t.id === targetId);
    const item = items.get(itemId);
    if (!target || !item) return;
    const next: Record<string, string[]> = {};
    for (const [t, list] of Object.entries(placements)) next[t] = item.reusable ? list : list.filter((x) => x !== itemId);
    const current = next[targetId] ?? [];
    if (current.includes(itemId) || current.length >= target.max_items) return;
    next[targetId] = [...current, itemId];
    onChange({ placements: next });
    setPicked(null);
  };
  const remove = (targetId: string, itemId: string) =>
    onChange({ placements: { ...placements, [targetId]: (placements[targetId] ?? []).filter((x) => x !== itemId) } });
  const onDragEnd = (e: DragEndEvent) => e.over && place(String(e.active.id), String(e.over.id));

  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      {q.background && <div className="dd-bg"><ImageView block={q.background} /></div>}
      <div className="dragdrop">
        <div className="tray" aria-label="Itens">
          <h4>Itens</h4>
          <div className="tray-items">
            {q.items.filter((i) => i.reusable || !used.has(i.id)).map((i) => (
              <Chip key={i.id} item={i} disabled={locked} selected={picked === i.id} onPick={() => setPicked(picked === i.id ? null : i.id)} />
            ))}
          </div>
          {picked && <p className="muted">Item selecionado: clique em um destino para colocá-lo.</p>}
        </div>
        <div className="targets">
          {q.targets.map((t) => {
            const list = placements[t.id] ?? [];
            const want = key?.[t.id];
            return (
              <Zone key={t.id} id={t.id} full={list.length >= t.max_items}>
                <div className="target-head">
                  <BlockView blocks={t.blocks} inline />
                  <span className="muted">{list.length}/{t.max_items}</span>
                </div>
                <div className="target-items">
                  {list.map((id) => {
                    const ok = want ? want.includes(id) : undefined;
                    return (
                      <span key={id} className={`placed ${ok === undefined ? "" : ok ? "is-correct" : "is-wrong"}`}>
                        {items.get(id) && <BlockView blocks={items.get(id)!.blocks} inline />}
                        {!locked && <button className="icon-btn" aria-label="Remover item" onClick={() => remove(t.id, id)}>×</button>}
                      </span>
                    );
                  })}
                  {!locked && picked && <Button variant="secondary" onClick={() => place(picked, t.id)}>Colocar aqui</Button>}
                </div>
                {want && <p className="muted">Correto: {want.map((id) => items.get(id)?.blocks.map((b) => (b.type === "paragraph" ? b.text : "")).join(" ") ?? id).join(", ") || "—"}</p>}
              </Zone>
            );
          })}
        </div>
      </div>
    </DndContext>
  );
}
