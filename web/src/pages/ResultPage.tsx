import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ExamResult, Outcome, ResultDetail } from "../api/types";
import { CasePanel, Exhibits, Html } from "../components/Content";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, Loaded } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { formatDuration, formatPct } from "../lib/format";
import { navigate } from "../lib/route";

const LABEL: Record<Outcome, { text: string; tone: "good" | "bad" | "neutral" | "warn" }> = {
  correct: { text: "Correta", tone: "good" },
  incorrect: { text: "Errada", tone: "bad" },
  unanswered: { text: "Em branco", tone: "neutral" },
  self_correct: { text: "Acertou (autoavaliada)", tone: "good" },
  self_incorrect: { text: "Errou (autoavaliada)", tone: "bad" },
};
type Filter = "all" | "wrong" | "blank" | "self";
const isWrong = (o: Outcome) => o === "incorrect" || o === "self_incorrect";

export function ResultPage({ id }: { id: string }) {
  const result = useAsync(() => api.result(id), [id]);
  useEffect(() => {
    if (result.error && /ainda n[ãa]o foi encerrada/i.test(result.error)) navigate("exam", id);
  }, [result.error, id]);
  return <Loaded state={result}>{(r) => <Result result={r} />}</Loaded>;
}

function Result({ result }: { result: ExamResult }) {
  const toast = useToast();
  const [filter, setFilter] = useState<Filter>("all");
  const s = result.summary;
  const wrongCount = result.details.filter((d) => isWrong(d.outcome)).length;

  const shown = result.details.filter((d) =>
    filter === "all" ? true : filter === "wrong" ? isWrong(d.outcome) : filter === "blank" ? d.outcome === "unanswered" : d.outcome.startsWith("self"),
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
          <div className="score">
            <span className="score-value">{formatPct(s.auto_pct)}</span>
            <span className="score-label">Pontuação automática</span>
            <span className="muted">{s.auto_correct} de {s.auto_total} corretas</span>
          </div>
          <div className="score">
            <span className="score-value">{formatPct(s.self_pct)}</span>
            <span className="score-label">Autoavaliada</span>
            <span className="muted">{s.self_total ? `${s.self_correct} de ${s.self_total} acertos declarados` : "sem questões interativas"}</span>
          </div>
          <div className="score">
            <span className="score-value">{formatDuration(result.duration_seconds)}</span>
            <span className="score-label">Tempo</span>
            <span className="muted">{s.unanswered} em branco</span>
          </div>
        </div>
        <p className="muted">O percentual é o acerto real neste teste. Exames oficiais usam outra escala; este valor não é a nota oficial.</p>
        <div className="actions">
          <Button variant="primary" onClick={redo} disabled={wrongCount === 0}>Refazer só as erradas ({wrongCount})</Button>
          <Button onClick={() => navigate("simulado", "new", { exam: result.spec.exam_ids[0] ?? "" })}>Novo simulado</Button>
          <Button variant="ghost" onClick={() => navigate("library")}>Biblioteca</Button>
        </div>
      </Card>

      <div className="seg" role="group" aria-label="Filtrar resultado">
        {(["all", "wrong", "blank", "self"] as Filter[]).map((f) => (
          <button key={f} className={filter === f ? "is-on" : ""} onClick={() => setFilter(f)}>
            {{ all: "Todas", wrong: "Erradas", blank: "Em branco", self: "Autoavaliadas" }[f]}
          </button>
        ))}
      </div>

      {shown.map((d) => <Detail key={d.question_id} d={d} result={result} index={result.details.indexOf(d) + 1} />)}
      {shown.length === 0 && <p className="muted">Nenhuma questão neste filtro.</p>}
    </div>
  );
}

function Detail({ d, result, index }: { d: ResultDetail; result: ExamResult; index: number }) {
  const label = LABEL[d.outcome];
  const study = d.case_id ? result.cases[d.case_id] : undefined;
  return (
    <Card className={`detail detail-${d.outcome}`}>
      <header className="row-between">
        <div className="chips"><Badge tone="info">#{index} · T{d.topic} Q{d.number}</Badge><Badge tone={label.tone}>{label.text}</Badge></div>
      </header>
      {study && <CasePanel study={study} defaultOpen={false} />}
      <Html html={d.stem} />
      <Exhibits images={d.images.filter((i) => i.role === "stem")} />
      {d.kind !== "interactive" ? (
        <ul className="choice-review">
          {d.choices.map((c) => {
            const correct = d.answer?.includes(c.letter);
            const picked = d.selected.includes(c.letter);
            return (
              <li key={c.letter} className={`${correct ? "is-correct" : ""} ${picked && !correct ? "is-wrong" : ""}`}>
                <span className="choice-letter">{c.letter}</span> {c.text}
                {picked && <Badge>sua resposta</Badge>}{correct && <Badge tone="good">correta</Badge>}
              </li>
            );
          })}
        </ul>
      ) : (
        <Exhibits images={d.images.filter((i) => i.role === "answer")} label="Resposta" />
      )}
      {d.explanation && <p className="explanation">{d.explanation}</p>}
    </Card>
  );
}
