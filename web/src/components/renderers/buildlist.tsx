import { closestCenter, DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Option } from "../../api/question";
import { BlockView } from "../BlockView";
import { Button } from "../ui";
import type { Of, RendererProps } from "./types";

function Row({ id, option, onRemove, locked, state }: { id: string; option: Option; onRemove: () => void; locked?: boolean; state?: string }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id, disabled: locked });
  return (
    <li ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} className={`seq-item ${isDragging ? "is-dragging" : ""} ${state ?? ""}`}>
      <button className="drag-handle" {...attributes} {...listeners} aria-label="Arrastar para reordenar (Espaço e setas)" disabled={locked}>⋮⋮</button>
      <div className="seq-body"><BlockView blocks={option.blocks} inline /></div>
      {!locked && <Button variant="ghost" onClick={onRemove} aria-label="Remover da sequência">✕</Button>}
    </li>
  );
}

export function BuildListRenderer({ q, value, onChange, locked, solution }: RendererProps<Of<"build_list">>) {
  const sequence = value?.sequence ?? [];
  const byId = new Map(q.pool.map((o) => [o.id, o]));
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));
  const correct = (solution?.key?.answer_sequence as string[] | undefined) ?? null;
  const onDragEnd = (e: DragEndEvent) => {
    if (!e.over || e.active.id === e.over.id) return;
    onChange({ sequence: arrayMove(sequence, sequence.indexOf(String(e.active.id)), sequence.indexOf(String(e.over.id))) });
  };
  return (
    <div className="buildlist">
      <div>
        <h4>Itens disponíveis</h4>
        <ul className="pool">
          {q.pool.filter((o) => !sequence.includes(o.id)).map((o) => (
            <li key={o.id}>
              <Button disabled={locked} onClick={() => onChange({ sequence: [...sequence, o.id] })}>
                <BlockView blocks={o.blocks} inline /> <span aria-hidden>＋</span>
              </Button>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h4>Sua sequência <span className="muted">({sequence.length}/{q.answer_length})</span></h4>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={sequence} strategy={verticalListSortingStrategy}>
            <ol className="sequence" aria-label="Sequência escolhida">
              {sequence.map((id, i) => byId.get(id) && (
                <Row key={id} id={id} option={byId.get(id)!} locked={locked}
                  state={correct ? (correct[i] === id ? "is-correct" : "is-wrong") : undefined}
                  onRemove={() => onChange({ sequence: sequence.filter((x) => x !== id) })} />
              ))}
              {sequence.length === 0 && <li className="muted">Adicione os itens na ordem correta.</li>}
            </ol>
          </SortableContext>
        </DndContext>
      </div>
    </div>
  );
}
