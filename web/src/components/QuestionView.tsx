import { useState } from "react";
import { QTYPE_LABEL, type PublicQuestion, type ResponseValue } from "../api/question";
import { BlockView } from "./BlockView";
import { RENDERERS } from "./renderers";
import { Badge, Button, Notice } from "./ui";

interface Props {
  question: PublicQuestion;
  response: ResponseValue | undefined;
  locked?: boolean;
  onChange: (value: ResponseValue) => void;
  /** Busca o gabarito (modo estudo, tipos autoavaliados ou prova encerrada). */
  reveal?: () => Promise<PublicQuestion>;
  revealed?: PublicQuestion | null;
}

export function QuestionView({ question: q, response, locked, onChange, reveal, revealed }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const Renderer = RENDERERS[q.type];
  const selfGraded = q.type === "self_assessed";

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
        <Badge>{QTYPE_LABEL[q.type]}</Badge>
        {q.type === "multiple_select" && <Badge tone="warn">Selecione {q.required_count}</Badge>}
        {q.conversion.status !== "ok" && <Badge tone="warn">Convertida com avisos</Badge>}
      </header>
      <BlockView blocks={q.prompt} />
      <Renderer q={q} value={response} onChange={onChange} locked={locked} solution={revealed} reveal={reveal} />
      {!selfGraded && reveal && !revealed && <Button variant="ghost" busy={busy} onClick={doReveal}>Mostrar resposta</Button>}
      {!selfGraded && revealed && <KeySummary q={revealed} />}
      {error && <Notice tone="bad">{error}</Notice>}
    </article>
  );
}

/** Resumo textual do gabarito, para os tipos em que o próprio renderizador não o exibe. */
export function KeySummary({ q }: { q: PublicQuestion }) {
  const key = q.key ?? {};
  return (
    <Notice tone="good">
      {q.type === "multiple_choice" && <>Resposta: <strong>{q.options.findIndex((o) => o.id === key.correct) >= 0 ? String.fromCharCode(65 + q.options.findIndex((o) => o.id === key.correct)) : "—"}</strong></>}
      {q.type === "multiple_select" && <>Respostas: <strong>{(key.correct as string[] | undefined)?.map((id) => String.fromCharCode(65 + q.options.findIndex((o) => o.id === id))).join(", ")}</strong></>}
      {q.type === "hot_area" && <>Regiões corretas: <strong>{(key.correct as string[] | undefined)?.map((id) => q.shapes.find((s) => s.id === id)?.label || id).join(", ")}</strong></>}
      {q.type === "build_list" && <>Sequência correta: <strong>{(key.answer_sequence as string[] | undefined)?.map((_, i) => i + 1).join(" → ")}</strong> (veja a ordem destacada)</>}
      {q.type === "drag_drop" && <>O gabarito está destacado nos destinos.</>}
      {(q.type === "active_screen" || q.type === "lab") && <>Verificações: {((key.checks as Array<{ label: string }> | undefined) ?? []).map((c) => c.label).join("; ") || "conclusão da tela"}.</>}
      {q.explanation && q.explanation.length > 0 && <BlockView blocks={q.explanation} />}
    </Notice>
  );
}
