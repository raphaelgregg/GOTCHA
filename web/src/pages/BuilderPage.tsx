import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ExamInfo, Mode, OnlyFilter } from "../api/types";
import { useToast } from "../components/Toast";
import { Button, Card, EmptyState, Loaded, Notice } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { navigate } from "../lib/route";

const ONLY: Record<OnlyFilter, string> = {
  all: "Todas as questões",
  wrong: "Só as que errei da última vez",
  marked: "Só as marcadas para revisão",
  unanswered: "Só as que nunca respondi",
};

export function BuilderPage({ preselected }: { preselected?: string }) {
  const exams = useAsync(() => api.exams());
  return (
    <Loaded state={exams}>
      {(list) =>
        list.filter((e) => e.question_count > 0).length === 0 ? (
          <Card><EmptyState title="Você ainda não tem questões">Importe e confirme um simulado na biblioteca para montar um teste.</EmptyState></Card>
        ) : (
          <Builder exams={list.filter((e) => e.question_count > 0)} preselected={preselected} />
        )
      }
    </Loaded>
  );
}

function Builder({ exams, preselected }: { exams: ExamInfo[]; preselected?: string }) {
  const toast = useToast();
  const [selected, setSelected] = useState<string[]>(preselected && exams.some((e) => e.id === preselected) ? [preselected] : exams.length === 1 ? [exams[0]!.id] : []);
  const [topics, setTopics] = useState<number[] | null>(null);
  const [count, setCount] = useState<string>("");
  const [shuffle, setShuffle] = useState(true);
  const [only, setOnly] = useState<OnlyFilter>("all");
  const [interactive, setInteractive] = useState(true);
  const [mode, setMode] = useState<Mode>("exam");
  const [minutes, setMinutes] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const chosen = exams.filter((e) => selected.includes(e.id));
  const total = chosen.reduce((sum, e) => sum + e.question_count, 0);
  const allTopics = [...new Set(chosen.flatMap((e) => e.topics))].sort((a, b) => a - b);

  useEffect(() => setTopics(null), [selected.join(",")]);

  const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  async function start() {
    setBusy(true);
    try {
      const { session_id } = await api.createSimulado({
        exam_ids: selected,
        topics: topics && topics.length > 0 && topics.length < allTopics.length ? topics : null,
        count: count ? Number(count) : null,
        shuffle,
        seed: shuffle ? Math.floor(Math.random() * 2 ** 31) : null,
        only,
        include_interactive: interactive,
        mode,
        time_limit_minutes: minutes ? Number(minutes) : null,
      });
      navigate("exam", session_id);
    } catch (e) {
      toast.show(messageOf(e), { tone: "bad" });
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={(e) => { e.preventDefault(); void start(); }}>
      <Card>
        <h2>Novo simulado</h2>
        <fieldset className="stack-sm">
          <legend>Exames</legend>
          {exams.map((e) => (
            <label key={e.id} className="check"><input type="checkbox" checked={selected.includes(e.id)} onChange={() => setSelected(toggle(selected, e.id))} /> {e.name} <span className="muted">({e.question_count})</span></label>
          ))}
        </fieldset>
        {allTopics.length > 1 && (
          <fieldset className="chips-input">
            <legend>Tópicos <span className="muted">(todos, se nenhum marcado)</span></legend>
            {allTopics.map((t) => (
              <label key={t} className="chip"><input type="checkbox" checked={topics?.includes(t) ?? false} onChange={() => setTopics(toggle(topics ?? [], t))} /> {t}</label>
            ))}
          </fieldset>
        )}
      </Card>

      <Card>
        <h3>Quais questões</h3>
        <div className="grid-2">
          <label className="field">Quantidade <span className="muted">(vazio = todas{total ? `, até ${total}` : ""})</span>
            <input type="number" min={1} value={count} onChange={(e) => setCount(e.target.value)} placeholder="Todas" />
          </label>
          <label className="field">Filtro
            <select value={only} onChange={(e) => setOnly(e.target.value as OnlyFilter)}>
              {(Object.keys(ONLY) as OnlyFilter[]).map((k) => <option key={k} value={k}>{ONLY[k]}</option>)}
            </select>
          </label>
        </div>
        <label className="check"><input type="checkbox" checked={shuffle} onChange={(e) => setShuffle(e.target.checked)} /> Ordem aleatória</label>
        <label className="check"><input type="checkbox" checked={interactive} onChange={(e) => setInteractive(e.target.checked)} /> Incluir questões interativas (autoavaliadas)</label>
      </Card>

      <Card>
        <h3>Como fazer</h3>
        <div className="mode-pick" role="radiogroup" aria-label="Modo">
          <label className={`mode ${mode === "exam" ? "is-on" : ""}`}><input type="radio" name="mode" checked={mode === "exam"} onChange={() => setMode("exam")} /><strong>Prova</strong><span>Sem gabarito durante o teste. Resultado no final.</span></label>
          <label className={`mode ${mode === "study" ? "is-on" : ""}`}><input type="radio" name="mode" checked={mode === "study"} onChange={() => setMode("study")} /><strong>Estudo</strong><span>Você pode mostrar a resposta de cada questão.</span></label>
        </div>
        <label className="field">Tempo limite em minutos <span className="muted">(vazio = sem limite)</span>
          <input type="number" min={1} value={minutes} onChange={(e) => setMinutes(e.target.value)} placeholder="Sem limite" />
        </label>
      </Card>

      {selected.length === 0 && <Notice tone="warn">Escolha ao menos um exame.</Notice>}
      <div className="sticky-bar">
        <Button type="button" onClick={() => navigate("library")}>Cancelar</Button>
        <Button variant="primary" type="submit" busy={busy} disabled={selected.length === 0}>Iniciar simulado</Button>
      </div>
    </form>
  );
}
