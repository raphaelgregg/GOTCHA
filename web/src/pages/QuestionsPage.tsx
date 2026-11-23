import { useState } from "react";
import { api } from "../api/client";
import { QTYPE_LABEL, type QType } from "../api/question";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, EmptyState, Loaded } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { plural } from "../lib/format";
import { navigate } from "../lib/route";

export function QuestionsPage({ examId }: { examId: string }) {
  const toast = useToast();
  const exams = useAsync(() => api.exams());
  const list = useAsync(() => api.examQuestions(examId), [examId]);
  const [type, setType] = useState<string>("all");
  const [onlyIssues, setOnlyIssues] = useState(false);
  const [newType, setNewType] = useState<QType>("multiple_choice");
  const exam = exams.data?.find((e) => e.id === examId);

  async function create() {
    try {
      const base = await api.template(newType);
      const created = await api.createQuestion(examId, { ...base, topic: 1, prompt: [{ type: "paragraph", text: "Novo enunciado" }] });
      navigate("question", String(created.uid));
    } catch (e) {
      toast.show(messageOf(e), { tone: "bad" });
    }
  }

  return (
    <Card>
      <div className="row-between">
        <h2>{exam?.name ?? "Exame"}: questões</h2>
        <Button variant="ghost" onClick={() => navigate("library")}>← Biblioteca</Button>
      </div>
      <div className="actions">
        <label className="field inline">Tipo
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="all">Todos</option>
            {(Object.keys(QTYPE_LABEL) as QType[]).map((t) => <option key={t} value={t}>{QTYPE_LABEL[t]}</option>)}
          </select>
        </label>
        <label className="check"><input type="checkbox" checked={onlyIssues} onChange={(e) => setOnlyIssues(e.target.checked)} /> Só com avisos ou anexos ausentes</label>
        <span className="spacer" />
        <label className="field inline">Nova questão
          <select value={newType} onChange={(e) => setNewType(e.target.value as QType)}>
            {(Object.keys(QTYPE_LABEL) as QType[]).map((t) => <option key={t} value={t}>{QTYPE_LABEL[t]}</option>)}
          </select>
        </label>
        <Button variant="primary" onClick={create}>Criar</Button>
      </div>
      <Loaded state={list}>
        {(items) => {
          const shown = items.filter((q) => (type === "all" || q.type === type) && (!onlyIssues || q.status !== "ok" || q.missing_images > 0));
          return items.length === 0 ? (
            <EmptyState title="Este exame não tem questões" />
          ) : (
            <ul className="rows">
              {shown.map((q) => (
                <li key={q.id}>
                  <div>
                    <strong>T{q.topic} · Q{q.number}</strong> <Badge>{QTYPE_LABEL[q.type as QType] ?? q.type}</Badge>
                    {q.status !== "ok" && <Badge tone="warn">{q.status === "manual_required" ? "revisão manual" : "parcial"}</Badge>}
                    {q.missing_images > 0 && <Badge tone="warn">{plural(q.missing_images, "anexo ausente", "anexos ausentes")}</Badge>}
                    <div className="muted clamp">{q.text || "(sem texto)"}</div>
                  </div>
                  <Button onClick={() => navigate("question", q.id)}>Editar</Button>
                </li>
              ))}
              {shown.length === 0 && <li className="muted">Nenhuma questão neste filtro.</li>}
            </ul>
          );
        }}
      </Loaded>
    </Card>
  );
}
