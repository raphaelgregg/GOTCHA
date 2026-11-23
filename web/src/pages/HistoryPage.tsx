import { api } from "../api/client";
import { Badge, Button, Card, EmptyState, Loaded } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { formatDate, formatPct } from "../lib/format";
import { navigate } from "../lib/route";

export function HistoryPage() {
  const sessions = useAsync(() => api.sessions());
  return (
    <Card>
      <h2>Histórico</h2>
      <Loaded state={sessions}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState title="Nenhum teste ainda">Monte um simulado e ele aparecerá aqui.</EmptyState>
          ) : (
            <ul className="rows">
              {list.map((s) => (
                <li key={s.id}>
                  <div>
                    <strong>{formatDate(s.created_at)}</strong>
                    <div className="muted">{s.question_count} questões · {s.mode === "exam" ? "Prova" : "Estudo"}</div>
                  </div>
                  {s.finished_at ? (
                    <>
                      <Badge tone="good">{formatPct(s.auto_pct)} automática</Badge>
                      {s.self_pct !== null && <Badge>{formatPct(s.self_pct)} autoavaliada</Badge>}
                      <Button onClick={() => navigate("result", s.id)}>Ver resultado</Button>
                    </>
                  ) : (
                    <>
                      <Badge tone="warn">em andamento</Badge>
                      <Button variant="primary" onClick={() => navigate("exam", s.id)}>Continuar</Button>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )
        }
      </Loaded>
    </Card>
  );
}
