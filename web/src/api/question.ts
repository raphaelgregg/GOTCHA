import type { Shape } from "../lib/geometry";
import type { ScreenSpec } from "../lib/screen";

export interface ParagraphBlock { type: "paragraph"; text: string }
export interface HtmlBlock { type: "html"; html: string }
export interface TableBlock { type: "table"; rows: string[][]; header: boolean }
export interface CodeBlock { type: "code"; code: string; language: string }
export interface ImageBlock { type: "image"; asset: string | null; name: string; alt: string; width_pct: number; align: "left" | "center" | "right"; caption: string }
export interface AttachmentBlock { type: "attachment"; asset: string | null; label: string }
export type Block = ParagraphBlock | HtmlBlock | TableBlock | CodeBlock | ImageBlock | AttachmentBlock;

export type QType = "multiple_choice" | "multiple_select" | "build_list" | "drag_drop" | "hot_area" | "active_screen" | "lab" | "self_assessed";
export const QTYPE_LABEL: Record<QType, string> = {
  multiple_choice: "Múltipla escolha",
  multiple_select: "Múltipla seleção",
  build_list: "Build List",
  drag_drop: "Drag and Drop",
  hot_area: "Hot Area",
  active_screen: "Active Screen",
  lab: "Laboratório",
  self_assessed: "Autoavaliada",
};

export interface Option { id: string; blocks: Block[] }
export interface HotShape { id: string; label: string; geometry: Shape }
export interface DragItem { id: string; blocks: Block[]; reusable: boolean }
export interface DropTarget { id: string; blocks: Block[]; min_items: number; max_items: number; region: Shape | null }
export interface LabStep { id: string; title: string; instructions: Block[] }
export type LabMode = "simulated" | "external_instructions" | "real";

export interface Base {
  id: string; topic: number; number: number; prompt: Block[]; case_id: string | null;
  scoring: { points: number; partial: boolean };
  conversion: { status: "ok" | "partial" | "manual_required"; preserved: string[]; lost: string[]; warnings: string[]; original_snippet: string };
  interactive: boolean;
  /** Presentes só depois de revelar (estudo, autoavaliada ou prova encerrada). */
  key?: Record<string, unknown>;
  explanation?: Block[];
}
export type PublicQuestion = Base & (
  | { type: "multiple_choice"; options: Option[]; variant: "standard" | "true_false"; required_count: number }
  | { type: "multiple_select"; options: Option[]; required_count: number }
  | { type: "build_list"; pool: Option[]; answer_length: number }
  | { type: "drag_drop"; items: DragItem[]; targets: DropTarget[]; background: ImageBlock | null; aspect: number | null; ordered: boolean }
  | { type: "hot_area"; image: ImageBlock; aspect: number; shapes: HotShape[]; selection: { mode: "single" | "multiple"; required_count: number } }
  | { type: "active_screen"; screen: ScreenSpec; fidelity: "reconstructed" | "approximate" | "screenshot_only"; limitations: string[] }
  | { type: "lab"; mode: LabMode; objectives: string[]; environment: { kind: string; description: string }; resources: string[]; steps: LabStep[]; screen?: ScreenSpec }
  | { type: "self_assessed" }
);

/** Resposta do usuário: o formato depende do tipo (ver o servidor). */
export interface ResponseValue {
  selected?: string[];
  sequence?: string[];
  placements?: Record<string, string[]>;
  events?: Array<{ component: string; type: "click" | "change"; value?: unknown }>;
  attested?: string[];
  self_mark?: boolean | null;
}
