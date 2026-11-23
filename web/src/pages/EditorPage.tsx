import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import { QTYPE_LABEL, type PublicQuestion, type QType, type ResponseValue } from "../api/question";
import { BlocksEditor } from "../components/editor/BlocksEditor";
import { EDITORS } from "../components/editor/typeEditors";
import { type Q } from "../components/editor/util";
import { QuestionView } from "../components/QuestionView";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, ConfirmDialog, Loaded, Notice } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { navigate } from "../lib/route";

export function EditorPage({ uid }: { uid: string }) {
  const loaded = useAsync(() => api.getQuestion(uid), [uid]);
  return <Loaded state={loaded}>{(q) => <Editor initial={q as Q} />}</Loaded>;
}

function Editor({ initial }: { initial: Q }) {
  const toast = useToast();
  const [q, setQ] = useState<Q>(initial);
  const saved = useRef(JSON.stringify(initial));
  const [preview, setPreview] = useState<{ view: PublicQuestion | null; errors: string[] }>({ view: null, errors: [] });
  const [response, setResponse] = useState<ResponseValue | undefined>();
  const [busy, setBusy] = useState(false);
  const [confirmType, setConfirmType] = useState<QType | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const Panel = EDITORS[q.type as QType];
  const dirty = JSON.stringify(q) !== saved.current;
  const set = (patch: Q) => setQ((cur) => ({ ...cur, ...patch }));

  useEffect(() => {
    const t = window.setTimeout(() => {
      api.preview(q).then(setPreview).catch((e) => setPreview({ view: null, errors: [messageOf(e)] }));
    }, 350);
    return () => window.clearTimeout(t);
  }, [q]);
  useEffect(() => setResponse(undefined), [q.type]);

  const back = () => navigate("questions", q.exam_id);

  async function save() {
    setBusy(true);
    try {
      const out = await api.putQuestion(q.uid, q);
      setQ(out as Q);
      saved.current = JSON.stringify(out);
      toast.show("Questão salva.", { tone: "good" });
    } catch (e) {
      toast.show(messageOf(e), { tone: "bad" });
    } finally {
      setBusy(false);
    }
  }
  async function changeType(to: QType) {
    try {
      setQ((await api.convert(to, q)) as Q);
      setConfirmType(null);
    } catch (e) {
      toast.show(messageOf(e), { tone: "bad" });
    }
  }
  const warnings: string[] = q.conversion?.warnings ?? [];

  return (
    <div className="stack">
      <Card>
        <div className="row-between">
          <div className="chips">
            <h2>Editar questão</h2>
            <Badge tone="info">{QTYPE_LABEL[q.type as QType]}</Badge>
            {dirty && <Badge tone="warn">alterações não salvas</Badge>}
          </div>
          <div className="actions">
            <Button variant="ghost" onClick={back}>← Voltar</Button>
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>Excluir</Button>
            <Button variant="primary" busy={busy} disabled={!dirty || preview.errors.length > 0} onClick={save}>Salvar</Button>
          </div>
        </div>
        <div className="grid-3">
          <label className="field">Tipo
            <select value={q.type} onChange={(e) => (e.target.value !== q.type ? setConfirmType(e.target.value as QType) : undefined)}>
              {(Object.keys(QTYPE_LABEL) as QType[]).map((t) => <option key={t} value={t}>{QTYPE_LABEL[t]}</option>)}
            </select>
          </label>
          <label className="field">Tópico<input type="number" min={1} value={q.topic} onChange={(e) => set({ topic: Number(e.target.value) })} /></label>
          <label className="field">Número<input type="number" min={1} value={q.number} onChange={(e) => set({ number: Number(e.target.value) })} /></label>
        </div>
        {q.case_id && <p className="muted">Pertence a um estudo de caso. <Button variant="ghost" onClick={() => navigate("case", q.case_id)}>Editar o contexto compartilhado</Button></p>}
        {q.conversion?.status !== "ok" && (
          <Notice tone="warn">
            <strong>Esta questão foi convertida com avisos.</strong>
            <ul>{warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            {q.conversion?.lost?.length > 0 && <p>Não preservado: {q.conversion.lost.join(", ")}.</p>}
          </Notice>
        )}
      </Card>

      <div className="editor-grid">
        <div className="stack">
          <Card>
            <BlocksEditor label="Enunciado" blocks={q.prompt} onChange={(prompt) => set({ prompt })} />
          </Card>
          <Card>
            <h3>{QTYPE_LABEL[q.type as QType]}: conteúdo e gabarito</h3>
            <Panel q={q} set={set} />
          </Card>
          <Card>
            <BlocksEditor label="Explicação (opcional, aparece depois da resposta)" blocks={q.explanation ?? []} onChange={(explanation) => set({ explanation })} />
          </Card>
        </div>
        <div className="stack preview-col">
          <Card>
            <h3>Prévia (como na prova)</h3>
            {preview.errors.length > 0 && <Notice tone="bad"><strong>Corrija antes de salvar:</strong><ul>{preview.errors.map((e) => <li key={e}>{e}</li>)}</ul></Notice>}
            {preview.view && <QuestionView question={preview.view} response={response} onChange={setResponse} />}
          </Card>
        </div>
      </div>

      {confirmType && (
        <ConfirmDialog title="Converter o tipo da questão?" confirmLabel="Converter" onClose={() => setConfirmType(null)} onConfirm={() => void changeType(confirmType)}>
          <p>O enunciado, a explicação, o número e as imagens do enunciado são mantidos. O conteúdo e o gabarito específicos de <strong>{QTYPE_LABEL[q.type as QType]}</strong> serão substituídos por um modelo de <strong>{QTYPE_LABEL[confirmType]}</strong>, que você preenche em seguida. Nada é salvo até você clicar em Salvar.</p>
        </ConfirmDialog>
      )}
      {confirmDelete && (
        <ConfirmDialog title="Excluir questão" danger confirmLabel="Excluir" onClose={() => setConfirmDelete(false)}
          onConfirm={async () => { await api.deleteQuestionById(q.uid); toast.show("Questão excluída.", { tone: "good" }); back(); }}>
          <p>Esta questão e o histórico dela serão removidos. Não dá para desfazer.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}

export const useTypeList = () => useMemo(() => Object.keys(QTYPE_LABEL) as QType[], []);
