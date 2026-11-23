import type { PublicQuestion, ResponseValue } from "../../api/question";

export interface RendererProps<T extends PublicQuestion = PublicQuestion> {
  q: T;
  value: ResponseValue | undefined;
  onChange: (value: ResponseValue) => void;
  locked?: boolean;
  /** Visão com o gabarito, quando já pode ser mostrado. */
  solution?: PublicQuestion | null;
  reveal?: () => Promise<PublicQuestion>;
}
export type Of<K extends PublicQuestion["type"]> = Extract<PublicQuestion, { type: K }>;
export const letter = (i: number) => String.fromCharCode(65 + i);
