import { useState } from "react";
import { api } from "../api/client";
import type { CaseDoc } from "../api/types";
import { BlocksEditor } from "../components/editor/BlocksEditor";
import { nextId } from "../components/editor/util";
import { useToast } from "../components/Toast";
import { Button, Card, Loaded } from "../components/ui";
import { messageOf, useAsync } from "../hooks/useAsync";
import { navigate } from "../lib/route";

export function CasePage({ id }: { id: string }) {
  const loaded = useAsync(() => api.getCase(id), [id]);
  return <Loaded state={loaded}>{(c) => <CaseEditor initial={c} />}</Loaded>;
}

function CaseEditor({ initial }: { initial: CaseDoc }) {
  const toast = useToast();
  const [doc, setDoc] = useState<CaseDoc>(initial);
  const ids = initial.question_ids ?? [];
  async function save() {
    try {
      await api.putCase(doc.id, doc);
      toast.show("Estudo de caso salvo.", { tone: "good" });
    } catch (e) {
      toast.show(messageOf(e), { tone: "bad" });
    }
  }
  return (
    <div className="stack">
      <Card>
        <div className="row-between">
          <h2>Estudo de caso</h2>
          <div className="actions"><Button variant="ghost" onClick={() => history.back()}>← Voltar</Button><Button variant="primary" onClick={save}>Salvar</Button></div>
        </div>
        <p className="muted">O contexto é guardado uma única vez e vale para as {ids.length} questões ligadas a ele.</p>
        <label className="field">Título<input value={doc.title} onChange={(e) => setDoc({ ...doc, title: e.target.value })} /></label>
      </Card>
      {doc.sections.map((s, i) => (
        <Card key={s.id}>
          <div className="row-between">
            <input className="inline-input" value={s.title} aria-label="Título da seção" onChange={(e) => setDoc({ ...doc, sections: doc.sections.map((x, k) => (k === i ? { ...x, title: e.target.value } : x)) })} />
            <Button variant="ghost" onClick={() => setDoc({ ...doc, sections: doc.sections.filter((_, k) => k !== i) })} aria-label="Remover seção">✕</Button>
          </div>
          <BlocksEditor blocks={s.blocks} onChange={(blocks) => setDoc({ ...doc, sections: doc.sections.map((x, k) => (k === i ? { ...x, blocks } : x)) })} />
        </Card>
      ))}
      <Button onClick={() => setDoc({ ...doc, sections: [...doc.sections, { id: nextId(doc.sections.map((s) => s.id), "secao"), title: "Nova seção", blocks: [{ type: "paragraph", text: "" }] }] })}>+ Seção</Button>
      <Card>
        <h3>Questões deste caso</h3>
        <ul className="rows">{ids.map((qid) => <li key={qid}><span className="mono">{qid}</span><Button onClick={() => navigate("question", qid)}>Editar questão</Button></li>)}</ul>
      </Card>
    </div>
  );
}
