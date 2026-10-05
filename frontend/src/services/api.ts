import type {
  BackgroundJob,
  Deck,
  Flashcard,
  ImportResult,
  Page,
  ReviewItem,
  ReviewStats,
  SpreadsheetPreview,
  SpreadsheetValidation,
  Subject,
  Topic,
  UploadedFile,
} from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new ApiError("Não foi possível conectar à API.", 0);
  }

  const contentType = response.headers.get("content-type") ?? "";
  const body: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String(body.detail)
        : `Falha na requisição (${response.status}).`;
    throw new ApiError(detail, response.status);
  }
  return body as T;
}

function jsonRequest(method: "POST" | "PUT", value: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  };
}

function queryString(values: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value) query.set(key, value);
  }
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  getReviewStats: () => request<ReviewStats>("/reviews/stats"),
  getDueCards: (pageSize = 20, filters: { deck_id?: string; topic_ids?: string[] } = {}) => {
    const query = new URLSearchParams({ page: "1", page_size: String(pageSize) });
    if (filters.deck_id) query.set("deck_id", filters.deck_id);
    filters.topic_ids?.forEach((topicId) => query.append("topic_ids", topicId));
    return request<Page<Flashcard & { next_review_at: string | null }>>(`/reviews/due?${query.toString()}`);
  },
  getReviewHistory: (pageSize = 10) =>
    request<Page<ReviewItem>>(`/reviews/history?page=1&page_size=${pageSize}`),
  submitReview: (cardId: string, rating: number) =>
    request<ReviewItem>(`/cards/${cardId}/review`, jsonRequest("POST", { rating })),
  listSubjects: () => request<Page<Subject>>("/subjects?page_size=100"),
  listTopics: (subjectId?: string) =>
    request<Page<Topic>>(`/topics${queryString({ page_size: "100", subject_id: subjectId })}`),
  listDecks: () => request<Page<Deck>>("/decks?page_size=100"),
  createSubject: (name: string) =>
    request<Subject>("/subjects", jsonRequest("POST", { name })),
  createTopic: (subjectId: string, name: string) =>
    request<Topic>("/topics", jsonRequest("POST", { subject_id: subjectId, name })),
  createDeck: (payload: { name: string; description: string; subject_id: string | null }) =>
    request<Deck>("/decks", jsonRequest("POST", payload)),
  updateDeck: (
    id: string,
    payload: { name: string; description: string; subject_id: string | null },
  ) => request<Deck>(`/decks/${id}`, jsonRequest("PUT", payload)),
  deleteDeck: (id: string) => request<void>(`/decks/${id}`, { method: "DELETE" }),
  listCards: (filters: { deck_id?: string; search?: string; page?: number; page_size?: number } = {}) => {
    const query = new URLSearchParams();
    query.set("page", String(filters.page ?? 1));
    query.set("page_size", String(filters.page_size ?? 50));
    if (filters.deck_id) query.set("deck_id", filters.deck_id);
    if (filters.search) query.set("search", filters.search);
    return request<Page<Flashcard>>(`/cards?${query.toString()}`);
  },
  createCard: (payload: Omit<Flashcard, "id" | "created_at">) =>
    request<Flashcard>("/cards", jsonRequest("POST", payload)),
  updateCard: (id: string, payload: Omit<Flashcard, "id" | "created_at">) =>
    request<Flashcard>(`/cards/${id}`, jsonRequest("PUT", payload)),
  deleteCard: (id: string) => request<void>(`/cards/${id}`, { method: "DELETE" }),
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadedFile>("/files/upload", { method: "POST", body: form });
  },
  previewFile: (id: string, sheetName?: string) => {
    const query = queryString({ sheet_name: sheetName, limit: "20" });
    return request<SpreadsheetPreview>(`/files/${id}/preview${query}`);
  },
  validateFile: (
    id: string,
    sheetName: string,
    mapping: Record<string, number>,
  ) =>
    request<SpreadsheetValidation>(
      `/files/${id}/validate`,
      jsonRequest("POST", { sheet_name: sheetName, mapping }),
    ),
  importFile: (
    payload: {
      file_id: string;
      deck_id: string;
      sheet_name: string;
      mapping: Record<string, number>;
    },
  ) => request<ImportResult>("/imports", jsonRequest("POST", payload)),
  enqueueAIGeneration: (payload: {
    subject: string;
    topic: string;
    content: string;
    quantity: number;
    difficulty: string;
    objective: string;
    language: string;
    deck_id: string | null;
  }) => request<BackgroundJob>("/jobs/ai-generations", jsonRequest("POST", payload)),
  getJob: (id: string) => request<BackgroundJob>(`/jobs/${id}`),
  retryJob: (id: string) => request<BackgroundJob>(`/jobs/${id}/retry`, jsonRequest("POST", {})),
};
