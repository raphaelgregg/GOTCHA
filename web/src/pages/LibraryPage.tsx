import { useState } from "react";
import { api } from "../api/client";
import type { ExamInfo } from "../api/types";
import { ImportDropzone } from "../components/ImportDropzone";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, ConfirmDialog, EmptyState, Loaded, Modal } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { plural } from "../lib/format";
import { navigate } from "../lib/route";

export function LibraryPage() {
  const exams = useAsync(() => api.exams());
  const drafts = useAsync(() => api.batches());
  const toast = useToast();
  const [renaming, setRenaming] = useState<ExamInfo | null>(null);
  const [removing, setRemoving] = useState<ExamInfo | null>(null);
  const [name, setName] = useState("");

  const refresh = () => { exams.reload(); drafts.reload(); };

  async function run(action: () => Promise<unknown>, done: string) {
    try {
      await action();
      toast.show(done, { tone: "good" });
      refresh();
    } catch (e) {
      toast.show(messageOf(e), { tone: "bad" });
    }
  }

  return (
    <div className="stack">
      <Card>
        <h2>Importar simulados</h2>
        <ImportDropzone onImported={refresh} />
      </Card>

      <Loaded state={drafts}>
        {(list) =>
          list.length > 0 && (
            <Card>
              <h2>Para revisar</h2>
              <p className="muted">Nada entra na biblioteca antes de você confirmar.</p>
              <ul className="rows">
                {list.map((b) => (
                  <li key={b.id}>
                    <div>
                      <strong>{b.filename}</strong>
                      <div className="muted">{plural(b.count, "questão", "questões")} · {b.format.toUpperCase()}</div>
                    </div>
                    {b.warning_count > 0 && <Badge tone="warn">{plural(b.warning_count, "aviso", "avisos")}</Badge>}
                    <Button variant="primary" onClick={() => navigate("batch", b.id)}>Revisar</Button>
                    <Button variant="ghost" onClick={() => run(() => api.discard(b.id), "Rascunho descartado.")}>Descartar</Button>
                  </li>
                ))}
              </ul>
            </Card>
          )
        }
      </Loaded>

      <Card>
        <h2>Seus exames</h2>
        <Loaded state={exams}>
          {(list) =>
            list.length === 0 ? (
              <EmptyState title="Nenhum exame ainda">Importe um arquivo acima, revise as questões e confirme para começar a treinar.</EmptyState>
            ) : (
              <ul className="rows">
                {list.map((e) => (
                  <li key={e.id}>
                    <div>
                      <strong>{e.name}</strong>
                      <div className="muted">
                        {plural(e.question_count, "questão", "questões")} · {e.topics.length === 0 ? "sem tópicos" : plural(e.topics.length, "tópico", "tópicos")}
                      </div>
                    </div>
                    <Button variant="primary" disabled={e.question_count === 0} onClick={() => navigate("simulado", "new", { exam: e.id })}>Treinar</Button>
                    <a className="btn btn-ghost" href={api.exportUrl(e.id)} download>Exportar</a>
                    <Button variant="ghost" onClick={() => { setName(e.name); setRenaming(e); }}>Renomear</Button>
                    <Button variant="ghost" onClick={() => setRemoving(e)}>Remover</Button>
                  </li>
                ))}
              </ul>
            )
          }
        </Loaded>
      </Card>

      {renaming && (
        <Modal title="Renomear exame" onClose={() => setRenaming(null)}>
          <form className="modal-body" onSubmit={(ev) => { ev.preventDefault(); const target = renaming; setRenaming(null); void run(() => api.renameExam(target.id, name), "Nome atualizado."); }}>
            <label className="field">Nome<input autoFocus value={name} onChange={(e) => setName(e.target.value)} required /></label>
            <footer className="modal-foot"><Button onClick={() => setRenaming(null)}>Cancelar</Button><Button variant="primary" type="submit">Salvar</Button></footer>
          </form>
        </Modal>
      )}
      {removing && (
        <ConfirmDialog title="Remover exame" danger confirmLabel="Remover" onClose={() => setRemoving(null)}
          onConfirm={() => { const target = removing; setRemoving(null); void run(() => api.deleteExam(target.id), "Exame removido."); }}>
          <p>Remover <strong>{removing.name}</strong> apaga as {removing.question_count} questões e o histórico delas. Não dá para desfazer.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}
