import { useState } from "react";
import type { PublicQuestion, ResponseState } from "../api/types";
import { toggleChoice } from "../lib/choices";
import { Exhibits, Html } from "./Content";
import { Badge, Button, Notice } from "./ui";

interface Props {
  question: PublicQuestion;
  response: ResponseState | undefined;
  locked?: boolean;
  onSelect: (selected: string[]) => void;
  onSelfMark: (correct: boolean) => void;
  /** Busca a resposta (modo estudo, questão interativa ou prova encerrada). */
  reveal?: () => Promise<PublicQuestion>;
  revealed?: PublicQuestion | null;
}

export function QuestionView({ question: q, response, locked, onSelect, onSelfMark, reveal, revealed }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selected = response?.selected ?? [];
  const required = q.required_count ?? 1;
  const interactive = q.kind === "interactive";
  const solution = revealed ?? null;

  async function doReveal() {
    if (!reveal) return;
    setBusy(true);
    setError(null);
    try {
      await reveal();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível mostrar a resposta.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="question">
      <header className="question-meta">
        <Badge tone="info">Tópico {q.topic} · Questão {q.number}</Badge>
        {q.kind === "multiple" && <Badge tone="warn">Selecione {required}</Badge>}
        {interactive && <Badge tone="warn">Interativa: autoavaliação</Badge>}
      </header>
      <Html html={q.stem} className="stem" />
      <Exhibits images={q.images.filter((i) => i.role === "stem")} />

      {!interactive && (
        <fieldset className="choices" disabled={locked}>
          <legend className="sr-only">Alternativas</legend>
          {q.choices.map((c) => {
            const checked = selected.includes(c.letter);
            const correct = solution?.answer?.includes(c.letter);
            return (
              <label key={c.letter} className={`choice ${checked ? "is-selected" : ""} ${solution ? (correct ? "is-correct" : checked ? "is-wrong" : "") : ""}`}>
                <input
                  type={q.kind === "multiple" ? "checkbox" : "radio"}
                  name={`q-${q.id}`}
                  checked={checked}
                  onChange={() => onSelect(toggleChoice(selected, c.letter, q.kind, required))}
                />
                <span className="choice-letter">{c.letter}</span>
                <span className="choice-text">{c.text}</span>
              </label>
            );
          })}
        </fieldset>
      )}

      {interactive && (
        <div className="interactive">
          <Notice>Resolva por conta própria; depois revele a resposta e marque se acertou.</Notice>
          {!solution && reveal && <Button variant="primary" busy={busy} onClick={doReveal}>Revelar resposta</Button>}
          {solution && (
            <>
              <Exhibits images={solution.images.filter((i) => i.role === "answer")} label="Resposta" />
              {solution.explanation && <p className="explanation">{solution.explanation}</p>}
              <div className="self-mark" role="group" aria-label="Autoavaliação">
                <Button variant={response?.self_mark === true ? "primary" : "secondary"} onClick={() => onSelfMark(true)} disabled={locked}>✓ Acertei</Button>
                <Button variant={response?.self_mark === false ? "danger" : "secondary"} onClick={() => onSelfMark(false)} disabled={locked}>✗ Errei</Button>
              </div>
            </>
          )}
        </div>
      )}

      {!interactive && reveal && !solution && (
        <Button variant="ghost" busy={busy} onClick={doReveal}>Mostrar resposta</Button>
      )}
      {!interactive && solution && (
        <Notice tone="good">
          Resposta: <strong>{solution.answer?.join(", ") || "não informada"}</strong>
          {solution.explanation && <p className="explanation">{solution.explanation}</p>}
        </Notice>
      )}
      {error && <Notice tone="bad">{error}</Notice>}
    </article>
  );
}

