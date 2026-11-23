import { useState } from "react";
import type { PublicQuestion, ResponseValue } from "../api/types";
import { questionStatus } from "../lib/progress";

type Filter = "all" | "marked" | "blank";

export function QuestionList({
  questions,
  responses,
  marks,
  current,
  onPick,
}: {
  questions: PublicQuestion[];
  responses: Record<string, ResponseValue>;
  marks: Set<string>;
  current: number;
  onPick: (index: number) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const items = questions
    .map((q, index) => ({ q, index, status: questionStatus(q, responses[q.id], marks.has(q.id)) }))
    .filter(({ q, status }) => filter === "all" || (filter === "marked" ? marks.has(q.id) : status === "unanswered"));
  const count = (s: "marked" | "unanswered") => questions.filter((q) => (s === "marked" ? marks.has(q.id) : questionStatus(q, responses[q.id], false) === "unanswered")).length;
  return (
    <div>
      <div className="seg" role="group" aria-label="Filtrar questões">
        <button className={filter === "all" ? "is-on" : ""} onClick={() => setFilter("all")}>Todas ({questions.length})</button>
        <button className={filter === "marked" ? "is-on" : ""} onClick={() => setFilter("marked")}>Marcadas ({count("marked")})</button>
        <button className={filter === "blank" ? "is-on" : ""} onClick={() => setFilter("blank")}>Em branco ({count("unanswered")})</button>
      </div>
      <div className="qgrid">
        {items.map(({ q, index, status }) => (
          <button key={q.id} className={`qcell ${status} ${index === current ? "is-current" : ""}`} onClick={() => onPick(index)} aria-label={`Ir para a questão ${index + 1}: ${status === "answered" ? "respondida" : status === "marked" ? "marcada" : "em branco"}`}>
            {index + 1}
          </button>
        ))}
        {items.length === 0 && <p className="muted">Nenhuma questão neste filtro.</p>}
      </div>
      <p className="legend"><span className="dot answered" /> respondida <span className="dot marked" /> marcada <span className="dot unanswered" /> em branco</p>
    </div>
  );
}
