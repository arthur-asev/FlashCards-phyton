export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Subject {
  id: string;
  name: string;
  description: string | null;
}

export interface Topic {
  id: string;
  subject_id: string;
  name: string;
  description: string | null;
}

export interface Deck {
  id: string;
  name: string;
  description: string | null;
  subject_id: string | null;
  created_at: string;
}

export interface Flashcard {
  id: string;
  deck_id: string;
  topic_id: string | null;
  front: string;
  back: string;
  explanation: string | null;
  example: string | null;
  difficulty: string | null;
  source: string | null;
  tags: string[];
  created_at: string;
}

export interface UploadedFile {
  id: string;
  filename: string;
  mime_type: string;
  size: number;
  checksum: string;
  status: string;
}

export interface SpreadsheetPreview extends UploadedFile {
  preview: {
    format: string;
    size_bytes: number;
    checksum: string;
    sheet_names: string[];
    selected_sheet: string;
    columns: string[];
    rows: string[][];
    row_count: number;
    has_more: boolean;
  };
}

export interface ValidationIssue {
  row: number | null;
  code: string;
  message: string;
}

export interface SpreadsheetValidation {
  valid: boolean;
  checked_rows: number;
  valid_rows: number;
  issues: ValidationIssue[];
  normalized_rows: Record<string, string>[];
}

export interface ReviewStats {
  total_cards: number;
  reviewed_cards: number;
  pending_cards: number;
  due_cards: number;
  total_reviews: number;
}

export interface ReviewItem {
  id: string;
  card_id: string;
  rating: number;
  interval: number;
  ease: number;
  repetitions: number;
  reviewed_at: string;
  next_review_at: string | null;
  card?: Pick<Flashcard, "id" | "front" | "back">;
}

export interface GeneratedCard {
  front: string;
  back: string;
  explanation?: string | null;
  example?: string | null;
  difficulty?: string | null;
  tags: string[];
  source?: string | null;
}

export interface BackgroundJob {
  id: string;
  type: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";
  attempts: number;
  max_attempts: number;
  result: {
    provider: string;
    model: string;
    cards: GeneratedCard[];
  } | null;
  error_code: string | null;
  error_message: string | null;
}

export interface ImportResult {
  id: string;
  file_id: string;
  deck_id: string;
  status: "COMPLETED";
  total_rows: number;
  processed_rows: number;
  failed_rows: number;
}