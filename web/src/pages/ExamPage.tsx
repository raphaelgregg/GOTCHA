import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { PublicQuestion, ResponseState, SessionState } from "../api/types";
import { CasePanel } from "../components/Content";
import { QuestionList } from "../components/QuestionList";
import { QuestionView } from "../components/QuestionView";
import { useToast } from "../components/Toast";
import { Badge, Button, ConfirmDialog, Loaded, Modal } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { useCountdown } from "../hooks/useCountdown";
import { useKeys } from "../hooks/useKeys";
import { formatClock } from "../lib/format";
import { navigate } from "../lib/route";

export function ExamPage({ id }: { id: string }) {
  const session = useAsync(async () => {
    const s = await api.session(id);
    if (!s.finished && s.paused) await api.resume(id);
    return s;
  }, [id]);
  return <Loaded state={session}>{(s) => (s.finished ? <Redirect to={id} /> : <Runner initial={s} />)}</Loaded>;
}

function Redirect({ to }: { to: string }) {
  useEffect(() => navigate("result", to), [to]);
  return null;
}

function Runner({ initial }: { initial: SessionState }) {
  const toast = useToast();
  const sid = initial.id;
  const [index, setIndex] = useState(0);
  const [responses, setResponses] = useState<Record<string, ResponseState>>(initial.responses);
  const [marks, setMarks] = useState<Set<string>>(new Set(initial.marks));
  const [revealed, setRevealed] = useState<Record<string, PublicQuestion>>({});
  const [panel, setPanel] = useState(false);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [ending, setEnding] = useState(false);
  const finishing = useRef(false);

  const questions = initial.questions;
  const q = questions[index]!;
  const study = initial.mode === "study";

  const finish = useCallback(async () => {
    if (finishing.current) return;
    finishing.current = true;
    setEnding(true);
    try {
      await api.finish(sid);
      navigate("result", sid);
    } catch (e) {
      finishing.current = false;
      setEnding(false);
      toast.show(messageOf(e), { tone: "bad" });
    }
  }, [sid, toast]);

  const left = useCountdown(initial.remaining_seconds, true, () => {
    toast.show("O tempo acabou. Encerrando a prova…", { tone: "info" });
    void finish();
  });
  const low = left !== null && left <= 60;

  const save = useCallback(
    async (qid: string, next: ResponseState) => {
      setResponses((r) => ({ ...r, [qid]: next }));
      try {
        await api.answer(sid, qid, next);
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) void finish();
        else toast.show(`Não foi possível salvar a resposta: ${messageOf(e)}`, { tone: "bad" });
      }
    },
    [sid, finish, toast],
  );

  const select = (selected: string[]) => void save(q.id, { selected, self_mark: responses[q.id]?.self_mark ?? null });
  const selfMark = (correct: boolean) => void save(q.id, { selected: [], self_mark: correct });

  const toggleMark = useCallback(async () => {
    const next = !marks.has(q.id);
    setMarks((m) => { const c = new Set(m); next ? c.add(q.id) : c.delete(q.id); return c; });
    try { await api.mark(sid, q.id, next); } catch (e) { toast.show(messageOf(e), { tone: "bad" }); }
  }, [marks, q.id, sid, toast]);

  const reveal = async (): Promise<PublicQuestion> => {
    const solution = await api.solution(sid, q.id);
    setRevealed((r) => ({ ...r, [q.id]: solution }));
    return solution;
  };

  const go = useCallback((i: number) => setIndex(Math.min(questions.length - 1, Math.max(0, i))), [questions.length]);

  async function saveAndExit() {
    try { await api.pause(sid); navigate("library"); } catch (e) { toast.show(messageOf(e), { tone: "bad" }); }
  }

  const keys = useMemo(() => {
    const map: Record<string, () => void> = {
      arrowright: () => go(index + 1),
      arrowleft: () => go(index - 1),
      m: () => void toggleMark(),
    };
    if (q.kind !== "interactive") {
      q.choices.forEach((c) => {
        map[c.letter.toLowerCase()] = () => {
          const current = responses[q.id]?.selected ?? [];
          const required = q.required_count ?? 1;
          const next = q.kind === "multiple"
            ? current.includes(c.letter) ? current.filter((l) => l !== c.letter) : current.length < required ? [...current, c.letter].sort() : current
            : [c.letter];
          select(next);
        };
      });
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, q, responses, toggleMark, go]);
  useKeys(keys, !panel && !confirmEnd && !ending);

  const answered = questions.filter((x) => responses[x.id] && (x.kind === "interactive" ? responses[x.id]!.self_mark !== null : responses[x.id]!.selected.length > 0)).length;
  const caseStudy = q.case_id ? initial.cases[q.case_id] : undefined;

  return (
    <div className="exam">
      <header className="exam-bar">
        <div className="chips">
          <strong>Questão {index + 1} de {questions.length}</strong>
          <Badge tone={study ? "good" : "info"}>{study ? "Estudo" : "Prova"}</Badge>
        </div>
        <label className="check mark"><input type="checkbox" checked={marks.has(q.id)} onChange={() => void toggleMark()} /> Marcar (M)</label>
        {left !== null && <span className={`timer ${low ? "is-low" : ""}`} role="timer" aria-label="Tempo restante">⏱ {formatClock(left)}</span>}
      </header>

      <div className={caseStudy ? "exam-body with-case" : "exam-body"}>
        {caseStudy && <CasePanel study={caseStudy} />}
        <QuestionView
          key={q.id}
          question={q}
          response={responses[q.id]}
          onSelect={select}
          onSelfMark={selfMark}
          reveal={study || q.kind === "interactive" ? reveal : undefined}
          revealed={revealed[q.id] ?? null}
        />
      </div>

      <footer className="exam-nav">
        <Button onClick={() => go(index - 1)} disabled={index === 0}>← Anterior</Button>
        <Button variant="primary" onClick={() => go(index + 1)} disabled={index === questions.length - 1}>Próxima →</Button>
        <span className="spacer" />
        <Button onClick={() => setPanel(true)}>Lista ({answered}/{questions.length})</Button>
        <Button variant="ghost" onClick={saveAndExit}>Salvar e sair</Button>
        <Button variant="danger" onClick={() => setConfirmEnd(true)}>Encerrar</Button>
      </footer>
      <p className="hint muted">Atalhos: ← → navegar · M marcar · A–F escolher alternativa</p>

      {panel && (
        <Modal title="Lista de questões" onClose={() => setPanel(false)} wide>
          <div className="modal-body">
            <QuestionList questions={questions} responses={responses} marks={marks} current={index} onPick={(i) => { go(i); setPanel(false); }} />
          </div>
        </Modal>
      )}
      {confirmEnd && (
        <ConfirmDialog title="Encerrar a prova?" confirmLabel={ending ? "Encerrando…" : "Encerrar e ver resultado"} danger onClose={() => setConfirmEnd(false)} onConfirm={() => void finish()}>
          <p>Você respondeu {answered} de {questions.length} questões. {questions.length - answered > 0 && <strong>{questions.length - answered} ficarão em branco.</strong>} {marks.size > 0 && `${marks.size} estão marcadas para revisão.`}</p>
          <p className="muted">Depois de encerrar, não dá para alterar as respostas.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}

