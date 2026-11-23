import { useState } from "react";
import type { Block } from "../../api/question";
import { BlockView } from "../BlockView";
import { Button, Notice } from "../ui";
import type { RendererProps } from "./types";

export function SelfAssessedRenderer({ value, onChange, locked, solution, reveal }: RendererProps) {
  const [busy, setBusy] = useState(false);
  const answer = (solution?.key?.answer_blocks as Block[] | undefined) ?? null;
  return (
    <div className="interactive">
      <Notice>Resolva por conta própria; depois revele a resposta e marque se acertou.</Notice>
      {!answer && reveal && <Button variant="primary" busy={busy} onClick={async () => { setBusy(true); try { await reveal(); } finally { setBusy(false); } }}>Revelar resposta</Button>}
      {answer && (
        <>
          <h4>Resposta de referência</h4>
          <BlockView blocks={answer} />
          <div className="self-mark" role="group" aria-label="Autoavaliação">
            <Button variant={value?.self_mark === true ? "primary" : "secondary"} disabled={locked} onClick={() => onChange({ self_mark: true })}>✓ Acertei</Button>
            <Button variant={value?.self_mark === false ? "danger" : "secondary"} disabled={locked} onClick={() => onChange({ self_mark: false })}>✗ Errei</Button>
          </div>
        </>
      )}
    </div>
  );
}
