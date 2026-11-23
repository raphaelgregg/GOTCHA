import type { ComponentType } from "react";
import type { QType } from "../../api/question";
import { BuildListRenderer } from "./buildlist";
import { ChoiceRenderer } from "./choice";
import { DragDropRenderer } from "./dragdrop";
import { HotAreaRenderer } from "./hotarea";
import { LabRenderer } from "./lab";
import { ActiveScreenRenderer } from "./screen";
import { SelfAssessedRenderer } from "./selfassessed";
import type { RendererProps } from "./types";

/** Um renderizador por tipo de questão. Adicionar um tipo = adicionar uma entrada aqui. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const RENDERERS: Record<QType, ComponentType<RendererProps<any>>> = {
  multiple_choice: ChoiceRenderer,
  multiple_select: ChoiceRenderer,
  build_list: BuildListRenderer,
  drag_drop: DragDropRenderer,
  hot_area: HotAreaRenderer,
  active_screen: ActiveScreenRenderer,
  lab: LabRenderer,
  self_assessed: SelfAssessedRenderer,
};
