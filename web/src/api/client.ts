import type { PublicQuestion, ResponseValue } from "./question";
import type {
  BatchDetail,
  CaseDoc,
  QuestionSummary,
  BatchSummary,
  ConfirmResult,
  DraftQuestion,
  ExamInfo,
  ExamResult,
  ImportResult,
  SessionState,
  SessionSummary,
  Spec,
} from "./types";

export interface AssetInfo {
  id: string; mime: string; width: number | null; height: number | null; pages: number | null;
  size: number; names: string[]; default_alt: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-GOTCHA", "1");
  if (typeof init.body === "string") headers.set("Content-Type", "application/json");
  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = `Erro ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = "Dados inválidos na requisição.";
    } catch {
      /* corpo sem JSON */
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  exams: () => request<ExamInfo[]>("/exams"),
  renameExam: (id: string, name: string) => request(`/exams/${id}`, json("PATCH", { name })),
  deleteExam: (id: string) => request(`/exams/${id}`, json("DELETE")),
  exportUrl: (id: string) => `/api/exams/${id}/export`,

  importFiles: (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request<{ results: ImportResult[] }>("/import", { method: "POST", body: form });
  },
  batches: () => request<BatchSummary[]>("/batches"),
  batch: (id: string) => request<BatchDetail>(`/batches/${id}`),
  editQuestion: (id: string, index: number, patch: Partial<DraftQuestion>) =>
    request<DraftQuestion>(`/batches/${id}/questions/${index}`, json("PATCH", patch)),
  deleteQuestion: (id: string, index: number) =>
    request(`/batches/${id}/questions/${index}`, json("DELETE")),
  mergeQuestion: (id: string, index: number) =>
    request<DraftQuestion>(`/batches/${id}/questions/${index}/merge`, json("POST")),
  confirm: (id: string, target: { exam_id?: string; exam_name?: string }) =>
    request<ConfirmResult>(`/batches/${id}/confirm`, json("POST", target)),
  undo: (id: string) => request(`/batches/${id}/undo`, json("POST")),
  discard: (id: string) => request(`/batches/${id}`, json("DELETE")),
  assetUrl: (sha: string) => `/api/assets/${sha}`,
  examQuestions: (examId: string) => request<QuestionSummary[]>(`/exams/${examId}/questions`),
  getQuestion: (uid: string) => request<Record<string, unknown>>(`/questions/${uid}`),
  putQuestion: (uid: string, body: Record<string, unknown>) => request<Record<string, unknown>>(`/questions/${uid}`, json("PUT", body)),
  deleteQuestionById: (uid: string) => request(`/questions/${uid}`, json("DELETE")),
  getCase: (id: string) => request<CaseDoc>(`/cases/${id}`),
  putCase: (id: string, body: CaseDoc) => request<CaseDoc>(`/cases/${id}`, json("PUT", body)),
  uploadAsset: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<AssetInfo>("/assets", { method: "POST", body: form });
  },
  orphanAssets: () => request<string[]>("/assets/orphans"),
  assetInfo: (sha: string) => request<AssetInfo>(`/assets/${sha}/info`),
  preview: (body: Record<string, unknown>) => request<{ view: PublicQuestion | null; errors: string[] }>("/preview", json("POST", body)),
  template: (type: string, mode = "simulated") => request<Record<string, unknown>>(`/templates/${type}?mode=${mode}`),
  convert: (type: string, body: Record<string, unknown>, mode = "simulated") => request<Record<string, unknown>>(`/convert/${type}?mode=${mode}`, json("POST", body)),
  createQuestion: (examId: string, body: Record<string, unknown>) => request<Record<string, unknown>>(`/exams/${examId}/questions`, json("POST", body)),

  createSimulado: (spec: Partial<Spec> & { exam_ids: string[] }) =>
    request<{ session_id: string }>("/simulados", json("POST", spec)),
  sessions: () => request<SessionSummary[]>("/sessions"),
  session: (id: string) => request<SessionState>(`/sessions/${id}`),
  answer: (sid: string, qid: string, body: ResponseValue) =>
    request(`/sessions/${sid}/responses/${qid}`, json("PUT", body)),
  mark: (sid: string, qid: string, marked: boolean) =>
    request(`/sessions/${sid}/marks/${qid}`, json("PUT", { marked })),
  pause: (sid: string) => request(`/sessions/${sid}/pause`, json("POST")),
  resume: (sid: string) => request(`/sessions/${sid}/resume`, json("POST")),
  finish: (sid: string) => request<ExamResult>(`/sessions/${sid}/finish`, json("POST")),
  result: (sid: string) => request<ExamResult>(`/sessions/${sid}/result`),
  solution: (sid: string, qid: string) =>
    request<PublicQuestion>(`/sessions/${sid}/solution/${qid}`),
};
