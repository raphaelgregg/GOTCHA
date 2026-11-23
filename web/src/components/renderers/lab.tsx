import type { LabMode } from "../../api/question";
import { BlockView } from "../BlockView";
import { Notice } from "../ui";
import { ScreenPlayer } from "./screen";
import type { Of, RendererProps } from "./types";

const BANNER: Record<LabMode, { tone: "warn" | "info"; title: string; text: string }> = {
  simulated: { tone: "warn", title: "Laboratório simulado", text: "Simulação local do GOTCHA. Não é uma execução real de infraestrutura (Azure, AWS, Cisco ou outra)." },
  external_instructions: { tone: "info", title: "Instruções de laboratório externo", text: "Faça as etapas fora do GOTCHA, no seu próprio ambiente, e marque o que concluiu. A pontuação é autoavaliada." },
  real: { tone: "info", title: "Laboratório real (descrição)", text: "O GOTCHA apenas guarda as instruções. Ele não executa nem acessa nenhuma infraestrutura. A pontuação é autoavaliada." },
};

export function LabRenderer({ q, value, onChange, locked }: RendererProps<Of<"lab">>) {
  const banner = BANNER[q.mode];
  const attested = value?.attested ?? [];
  return (
    <div className="lab">
      <Notice tone={banner.tone}><strong>{banner.title}.</strong> {banner.text}</Notice>
      {q.environment.description && <p className="muted"><strong>Ambiente:</strong> {q.environment.description}</p>}
      {q.objectives.length > 0 && <><h4>Objetivos</h4><ul>{q.objectives.map((o) => <li key={o}>{o}</li>)}</ul></>}
      {q.resources.length > 0 && <><h4>Recursos necessários</h4><ul>{q.resources.map((r) => <li key={r}>{r}</li>)}</ul></>}
      <h4>Etapas</h4>
      <ol className="lab-steps">
        {q.steps.map((s) => (
          <li key={s.id}>
            <strong>{s.title}</strong>
            <BlockView blocks={s.instructions} />
            {q.mode !== "simulated" && (
              <label className="check"><input type="checkbox" disabled={locked} checked={attested.includes(s.id)}
                onChange={(e) => onChange({ ...value, attested: e.target.checked ? [...attested, s.id] : attested.filter((x) => x !== s.id) })} /> Concluí esta etapa</label>
            )}
          </li>
        ))}
      </ol>
      {q.mode === "simulated" && q.screen && (
        <ScreenPlayer spec={q.screen} events={value?.events ?? []} locked={locked} onEvents={(events) => onChange({ ...value, events })} />
      )}
    </div>
  );
}
