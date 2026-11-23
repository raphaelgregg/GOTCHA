import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ExamResult, Outcome, ResultDetail } from "../api/types";
import { CaseDocPanel } from "../components/BlockView";
import { QuestionView } from "../components/QuestionView";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, Loaded } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { formatDuration, formatPct } from "../lib/format";
import { evaluate } from "../lib/logic";
import { navigate } from "../lib/route";
import { replay, type ScreenSpec } from "../lib/screen";

const LABEL: Record<Outcome, { text: string; tone: "good" | "bad" | "neutral" | "warn" }> = {
  correct: { text: "Correta", tone: "good" },
  incorrect: { text: "Errada", tone: "bad" },
  partial: { text: "Parcial", tone: "warn" },
  unanswered: { text: "Em branco", tone: "neutral" },
  self_correct: { text: "Acertou (autoavaliada)", tone: "good" },
  self_incorrect: { text: "Errou (autoavaliada)", tone: "bad" },
};
type Filter = "all" | "wrong" | "blank" | "self";
const isWrong = (o: Outcome) => o === "incorrect" || o === "self_incorrect" || o === "partial";

export function ResultPage({ id }: { id: string }) {
  const result = useAsync(() => api.result(id), [id]);
  useEffect(() => {
    if (result.error && /ainda n[ãa]o foi encerrada/i.test(result.error)) navigate("exam", id);
  }, [result.error, id]);
  return <Loaded state={result}>{(r) => <Result result={r} />}</Loaded>;
}

function Score({ value, label, detail }: { value: string; label: string; detail: string }) {
  return (
    <div className="score">
      <span className="score-value">{value}</span>
      <span className="score-label">{label}</span>
      <span className="muted">{detail}</span>
    </div>
  );
}

function Result({ result }: { result: ExamResult }) {
  const toast = useToast();
  const [filter, setFilter] = useState<Filter>("all");
  const s = result.summary;
  const wrongCount = result.details.filter((d) => isWrong(d.outcome)).length;
  const shown = result.details.filter((d) =>
    filter === "all" ? true : filter === "wrong" ? isWrong(d.outcome) : filter === "blank" ? d.outcome === "unanswered" : d.group !== "auto",
  );

  async function redo() {
    try {
      const { session_id } = await api.createSimulado({ ...result.spec, only: "wrong", count: null, seed: Math.floor(Math.random() * 2 ** 31) });
      navigate("exam", session_id);
    } catch (e) {
      toast.show(e instanceof ApiError ? e.message : messageOf(e), { tone: "bad" });
    }
  }

  return (
    <div className="stack">
      <Card>
        <h2>Resultado</h2>
        <div className="scores">
          <Score value={formatPct(s.auto_pct)} label="Pontuação automática" detail={`${s.auto_correct} de ${s.auto_total} corretas`} />
          {s.self_total > 0 && <Score value={formatPct(s.self_pct)} label="Autoavaliada" detail={`${s.self_correct} de ${s.self_total} acertos declarados`} />}
          {s.lab_total > 0 && <Score value={formatPct(s.lab_pct)} label="Laboratório simulado" detail={`${s.lab_correct} de ${s.lab_total} (simulação local)`} />}
          <Score value={formatDuration(result.duration_seconds)} label="Tempo" detail={`${s.unanswered} em branco`} />
        </div>
        <p className="muted">O percentual é o acerto real neste teste, com crédito parcial quando a questão permite. Exames oficiais usam outra escala; este valor não é a nota oficial.</p>
        <div className="actions">
          <Button variant="primary" onClick={redo} disabled={wrongCount === 0}>Refazer só as erradas ({wrongCount})</Button>
          <Button onClick={() => navigate("simulado", "new", { exam: result.spec.exam_ids[0] ?? "" })}>Novo simulado</Button>
          <Button variant="ghost" onClick={() => navigate("library")}>Biblioteca</Button>
        </div>
      </Card>

      <div className="seg" role="group" aria-label="Filtrar resultado">
        {(["all", "wrong", "blank", "self"] as Filter[]).map((f) => (
          <button key={f} className={filter === f ? "is-on" : ""} onClick={() => setFilter(f)}>
            {{ all: "Todas", wrong: "Erradas", blank: "Em branco", self: "Autoavaliadas e laboratórios" }[f]}
          </button>
        ))}
      </div>

      {shown.map((d) => <Detail key={d.question_id} d={d} result={result} index={result.details.indexOf(d) + 1} />)}
      {shown.length === 0 && <p className="muted">Nenhuma questão neste filtro.</p>}
    </div>
  );
}

/** Para telas e laboratórios, mostra quais verificações passaram, reexecutando as ações no navegador. */
function Checks({ d }: { d: ResultDetail }) {
  if ((d.type !== "active_screen" && d.type !== "lab") || !d.key) return null;
  const spec = (d.type === "active_screen" ? d.screen : d.screen) as ScreenSpec | undefined;
  const checks = (d.key.checks as Array<{ id: string; label: string; when: unknown }> | undefined) ?? [];
  if (!spec || checks.length === 0) return null;
  const run = replay(spec, d.response.events ?? []);
  return (
    <ul className="checks">
      {checks.map((c) => {
        const ok = Boolean(evaluate(c.when, run.state));
        return <li key={c.id} className={ok ? "is-correct" : "is-wrong"}>{ok ? "✓" : "✗"} {c.label}</li>;
      })}
    </ul>
  );
}

function Detail({ d, result, index }: { d: ResultDetail; result: ExamResult; index: number }) {
  const label = LABEL[d.outcome];
  const study = d.case_id ? result.cases[d.case_id] : undefined;
  return (
    <Card className={`detail detail-${d.outcome}`}>
      <header className="row-between">
        <div className="chips">
          <Badge tone="info">#{index}</Badge><Badge tone={label.tone}>{label.text}</Badge>
          {d.outcome === "partial" && <Badge tone="warn">{Math.round(d.score * 100)}% do ponto</Badge>}
        </div>
      </header>
      {study && <CaseDocPanel study={study} defaultOpen={false} />}
      <QuestionView question={d} response={d.response} locked onChange={() => undefined} revealed={d} />
      <Checks d={d} />
    </Card>
  );
}
