export type Kind = "single" | "multiple" | "true_false" | "interactive";
export type Mode = "study" | "exam";
export type OnlyFilter = "all" | "wrong" | "marked" | "unanswered";

export interface Choice {
  letter: string;
  text: string;
}
export interface ImageRef {
  name: string;
  sha: string | null;
  role: "stem" | "answer";
  missing: boolean;
}
export interface CaseStudy {
  id: string;
  title: string;
  text: string;
}
export interface DraftQuestion {
  topic: number;
  number: number;
  kind: Kind;
  stem: string;
  choices: Choice[];
  answer: string[];
  explanation: string;
  images: ImageRef[];
  case_id: string | null;
  warnings: string[];
}
export interface BatchSummary {
  id: string;
  filename: string;
  format: string;
  title: string;
  status: string;
  exam_id: string | null;
  count: number;
  warning_count: number;
}
export interface BatchDetail extends BatchSummary {
  questions: DraftQuestion[];
  cases: CaseStudy[];
  warnings: string[];
}
export interface ImportResult {
  filename: string;
  ok: boolean;
  batch_id?: string;
  format?: string;
  count?: number;
  warning_count?: number;
  error?: string;
}
export interface ExamInfo {
  id: string;
  name: string;
  question_count: number;
  topics: number[];
}
export interface ConfirmResult {
  exam_id: string;
  added: number;
  skipped: number;
}

export interface PublicQuestion {
  id: string;
  topic: number;
  number: number;
  kind: Kind;
  stem: string;
  choices: Choice[];
  images: ImageRef[];
  case_id: string | null;
  required_count?: number;
  answer?: string[];
  explanation?: string;
}
export interface ResponseState {
  selected: string[];
  self_mark: boolean | null;
}
export interface Spec {
  exam_ids: string[];
  topics: number[] | null;
  count: number | null;
  shuffle: boolean;
  seed: number | null;
  only: OnlyFilter;
  include_interactive: boolean;
  mode: Mode;
  time_limit_minutes: number | null;
}
export interface SessionState {
  id: string;
  mode: Mode;
  finished: boolean;
  paused: boolean;
  remaining_seconds: number | null;
  time_limit_seconds: number | null;
  elapsed_seconds: number;
  questions: PublicQuestion[];
  responses: Record<string, ResponseState>;
  marks: string[];
  cases: Record<string, CaseStudy>;
}
export type Outcome = "correct" | "incorrect" | "unanswered" | "self_correct" | "self_incorrect";
export interface ResultDetail extends PublicQuestion {
  question_id: string;
  outcome: Outcome;
  selected: string[];
  self_mark: boolean | null;
}
export interface Summary {
  auto_total: number;
  auto_correct: number;
  self_total: number;
  self_correct: number;
  unanswered: number;
  auto_pct: number | null;
  self_pct: number | null;
}
export interface ExamResult {
  session_id: string;
  spec: Spec;
  summary: Summary;
  duration_seconds: number;
  details: ResultDetail[];
  cases: Record<string, CaseStudy>;
}
export interface SessionSummary {
  id: string;
  mode: Mode;
  created_at: number;
  finished_at: number | null;
  question_count: number;
  auto_pct: number | null;
  self_pct: number | null;
}
