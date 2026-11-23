import { useMemo, useState } from "react";
import { api } from "../api/client";
import type { BatchDetail, Choice, DraftQuestion, Kind } from "../api/types";
import { Exhibits, Html } from "../components/Content";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, Loaded, Notice } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { plural } from "../lib/format";
import { navigate } from "../lib/route";

const KIND_LABEL: Record<Kind, string> = {
  single: "Múltipla escolha",
  multiple: "Múltipla resposta",
  true_false: "Verdadeiro/Falso",
  interactive: "Interativa",
};

const stripTags = (html: string) =>
  html.replace(/<\/(p|div|li|tr)>|<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\n{2,}/g, "\n").trim();
const escapeHtml = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const textToHtml = (text: string) => text.split("\n").filter((l) => l.trim()).map((l) => `<p>${escapeHtml(l.trim())}</p>`).join("");

export function ReviewPage({ id }: { id: string }) {
  const batch = useAsync(() => api.batch(id), [id]);
  return <Loaded state={batch}>{(data) => <Review batch={data} reload={batch.reload} />}</Loaded>;
}

function Review({ batch, reload }: { batch: BatchDetail; reload: () => void }) {
  const [onlyWarnings, setOnlyWarnings] = useState(false);
  const v2 = batch.schema === 2;
  const total = v2 ? batch.questions_v2.length : batch.questions.length;
  const visible = useMemo(
    () => batch.questions.map((q, index) => ({ q, index })).filter(({ q }) => !onlyWarnings || q.warnings.length > 0),
    [batch.questions, onlyWarnings],
  );
  const withWarnings = v2 ? batch.questions_v2.filter((q) => q.warnings.length > 0 || q.status !== "ok").length : batch.questions.filter((q) => q.warnings.length > 0).length;

  return (
    <div className="stack">
      <Card>
        <div className="row-between">
          <div>
            <h2>Revisar: {batch.filename}</h2>
            <p className="muted">{plural(total, "questão", "questões")} · formato {batch.format.toUpperCase()} · {withWarnings} com avisos</p>
          </div>
          <Button variant="ghost" onClick={() => navigate("library")}>← Voltar</Button>
        </div>
        {batch.warnings.map((w) => <Notice key={w} tone="warn">{w}</Notice>)}
        {(batch.cases.length > 0 || batch.cases_v2.length > 0) && <Notice>{plural(batch.cases.length + batch.cases_v2.length, "estudo de caso", "estudos de caso")} com contexto compartilhado {batch.cases.length + batch.cases_v2.length === 1 ? "foi detectado" : "foram detectados"}.</Notice>}
        {v2 && <Notice>Pacote .gotcha: as questões já estão no modelo completo. Confirme para adicioná-las; edite depois em <strong>Questões</strong> do exame.</Notice>}
        {!v2 && <label className="check"><input type="checkbox" checked={onlyWarnings} onChange={(e) => setOnlyWarnings(e.target.checked)} /> Mostrar só questões com avisos</label>}
      </Card>

      {v2 && (
        <Card>
          <ul className="rows">
            {batch.questions_v2.map((q) => (
              <li key={q.id}>
                <div><strong>T{q.topic} · Q{q.number}</strong> <Badge>{q.type}</Badge>
                  {q.missing_images > 0 && <Badge tone="warn">{plural(q.missing_images, "anexo ausente", "anexos ausentes")}</Badge>}
                  <div className="muted clamp">{q.text}</div></div>
                {q.warnings.length > 0 && <Badge tone="warn">{plural(q.warnings.length, "aviso", "avisos")}</Badge>}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {!v2 && visible.length === 0 && <Notice tone="good">Nenhuma questão com avisos.</Notice>}
      {!v2 && visible.map(({ q, index }) => (
        <QuestionEditor key={`${index}-${q.number}-${q.stem.length}`} batchId={batch.id} index={index} q={q} last={index === batch.questions.length - 1} reload={reload} />
      ))}
      <ConfirmBar batch={batch} count={total} />
    </div>
  );
}

function ConfirmBar({ batch, count }: { batch: BatchDetail; count: number }) {
  const toast = useToast();
  const exams = useAsync(() => api.exams());
  const [target, setTarget] = useState("new");
  const [name, setName] = useState(batch.filename.replace(/\.[^.]+$/, ""));
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setBusy(true);
    try {
      const result = await api.confirm(batch.id, target === "new" ? { exam_name: name } : { exam_id: target });
      toast.show(
        `${result.added} questões adicionadas${result.skipped ? `, ${result.skipped} ignoradas por já existirem` : ""}${result.renumbered ? `, ${result.renumbered} renumeradas` : ""}.`,
        { tone: "good", ms: 20000, action: { label: "Desfazer", run: () => void api.undo(batch.id).then(() => toast.show("Importação desfeita.")).catch((e) => toast.show(messageOf(e), { tone: "bad" })) } },
      );
      navigate("library");
    } catch (e) {
      toast.show(messageOf(e), { tone: "bad" });
      setBusy(false);
    }
  }
  return (
    <div className="sticky-bar">
      <label className="field inline">Destino
        <select value={target} onChange={(e) => setTarget(e.target.value)}>
          <option value="new">Novo exame</option>
          {exams.data?.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
        </select>
      </label>
      {target === "new" && <label className="field inline">Nome<input value={name} onChange={(e) => setName(e.target.value)} /></label>}
      <Button variant="primary" busy={busy} disabled={count === 0 || (target === "new" && !name.trim())} onClick={confirm}>Confirmar {count} questões</Button>
    </div>
  );
}

function QuestionEditor({ batchId, index, q, last, reload }: { batchId: string; index: number; q: DraftQuestion; last: boolean; reload: () => void }) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ stem: stripTags(q.stem), topic: q.topic, number: q.number, kind: q.kind, answer: q.answer, choices: q.choices, explanation: q.explanation });
  const [busy, setBusy] = useState(false);

  async function act(fn: () => Promise<unknown>, ok?: string) {
    setBusy(true);
    try {
      await fn();
      if (ok) toast.show(ok, { tone: "good" });
      setEditing(false);
      reload();
    } catch (e) {
      toast.show(messageOf(e), { tone: "bad" });
    } finally {
      setBusy(false);
    }
  }

  const setChoice = (i: number, text: string) => setDraft({ ...draft, choices: draft.choices.map((c, k): Choice => (k === i ? { ...c, text } : c)) });
  const toggleAnswer = (letter: string) =>
    setDraft({ ...draft, answer: draft.answer.includes(letter) ? draft.answer.filter((l) => l !== letter) : [...draft.answer, letter].sort() });
  const addChoice = () => setDraft({ ...draft, choices: [...draft.choices, { letter: String.fromCharCode(65 + draft.choices.length), text: "" }] });
  const dropLastChoice = () => setDraft({ ...draft, choices: draft.choices.slice(0, -1), answer: draft.answer.filter((l) => l !== String.fromCharCode(64 + draft.choices.length)) });

  return (
    <Card className="editor">
      <header className="row-between">
        <div className="chips">
          <Badge tone="info">T{q.topic} · Q{q.number}</Badge>
          <Badge>{KIND_LABEL[q.kind]}</Badge>
          {q.warnings.length > 0 && <Badge tone="warn">{plural(q.warnings.length, "aviso", "avisos")}</Badge>}
        </div>
        <div className="actions">
          <Button variant="ghost" onClick={() => setEditing(!editing)}>{editing ? "Cancelar" : "Editar"}</Button>
          {!last && <Button variant="ghost" busy={busy} onClick={() => act(() => api.mergeQuestion(batchId, index), "Questões unidas.")}>Unir com a próxima</Button>}
          <Button variant="ghost" busy={busy} onClick={() => act(() => api.deleteQuestion(batchId, index))}>Excluir</Button>
        </div>
      </header>
      {q.warnings.map((w) => <Notice key={w} tone="warn">{w}</Notice>)}

      {!editing ? (
        <>
          <Html html={q.stem} />
          <Exhibits images={q.images} />
          <ol className="choice-preview" type="A">
            {q.choices.map((c) => <li key={c.letter} className={q.answer.includes(c.letter) ? "is-answer" : ""}>{c.text}{q.answer.includes(c.letter) && " ✓"}</li>)}
          </ol>
          {q.kind === "interactive" && <p className="muted">Sem alternativas: será autoavaliada com a imagem da resposta.</p>}
        </>
      ) : (
        <form className="stack-sm" onSubmit={(e) => { e.preventDefault(); void act(() => api.editQuestion(batchId, index, { ...draft, stem: textToHtml(draft.stem) }), "Questão atualizada."); }}>
          <div className="grid-3">
            <label className="field">Tópico<input type="number" min={1} value={draft.topic} onChange={(e) => setDraft({ ...draft, topic: Number(e.target.value) })} /></label>
            <label className="field">Número<input type="number" min={1} value={draft.number} onChange={(e) => setDraft({ ...draft, number: Number(e.target.value) })} /></label>
            <label className="field">Tipo
              <select value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value as Kind })}>
                {(Object.keys(KIND_LABEL) as Kind[]).map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
              </select>
            </label>
          </div>
          <label className="field">Enunciado (texto simples; tabelas e formatação serão removidas se você salvar)
            <textarea rows={6} value={draft.stem} onChange={(e) => setDraft({ ...draft, stem: e.target.value })} />
          </label>
          {draft.kind !== "interactive" && (
            <fieldset className="stack-sm">
              <legend>Alternativas e gabarito</legend>
              {draft.choices.map((c, i) => (
                <div key={c.letter} className="choice-edit">
                  <label className="check" title="Marcar como correta"><input type="checkbox" checked={draft.answer.includes(c.letter)} onChange={() => toggleAnswer(c.letter)} /> {c.letter}</label>
                  <input value={c.text} onChange={(e) => setChoice(i, e.target.value)} aria-label={`Texto da alternativa ${c.letter}`} />
                </div>
              ))}
              <div className="actions">
                <Button type="button" onClick={addChoice} disabled={draft.choices.length >= 6}>+ Alternativa</Button>
                <Button type="button" variant="ghost" onClick={dropLastChoice} disabled={draft.choices.length === 0}>− Última</Button>
              </div>
            </fieldset>
          )}
          <label className="field">Explicação (opcional)<textarea rows={2} value={draft.explanation} onChange={(e) => setDraft({ ...draft, explanation: e.target.value })} /></label>
          <div className="actions"><Button variant="primary" type="submit" busy={busy}>Salvar</Button></div>
        </form>
      )}
    </Card>
  );
}
