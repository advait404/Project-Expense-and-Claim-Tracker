export type ProjectStatus = "active" | "completed" | "on_hold" | "archived";

export interface Project {
  id: string;
  name: string;
  description?: string;
  start_date?: string;
  end_date?: string;
  budget?: number;
  status: ProjectStatus;
}

export interface ProjectSummary {
  project_id: string;
  project_name: string;
  total_income: number;
  total_expenses: number;
  net_position: number;
  total_claimed: number;
  total_unclaimed: number;
}

export type ExpenseSource = "manual" | "pdf";

export interface Expense {
  id: string;
  project_id: string;
  project_name?: string;
  date: string;
  vendor: string;
  description?: string;
  amount: number;
  currency: string;
  category: string;
  is_claimed: boolean;
  claimed_date?: string | null;
  notes?: string;
  source: ExpenseSource;
  currency_conversion_type?: string | null;
  original_value?: number | null;
  original_currency?: string | null;
  fx_rate?: number | null;
  fx_rate_timestamp?: string | null;
}

export interface Income {
  id: string;
  project_id: string;
  project_name?: string;
  date: string;
  source: string;
  amount: number;
  currency: string;
  notes?: string;
}

export interface ParsedTransaction {
  date: string;
  description: string;
  amount: number;
  currency: string;
  category_suggestion?: string;
}

export interface DuplicateWarning {
  is_duplicate: boolean;
  previously_uploaded_at?: string | null;
  previously_uploaded_filename?: string | null;
}

export interface PdfUploadResponse {
  upload_id: string;
  parsed_transactions: ParsedTransaction[];
  duplicate_warning: DuplicateWarning;
}

export interface PdfJobStatus {
  status: "processing" | "done" | "error";
  result?: PdfUploadResponse;
  detail?: string;
}

export const EXPENSE_CATEGORIES = [
  "Travel",
  "Meals",
  "Accommodation",
  "Equipment",
  "Software",
  "Supplies",
  "Services",
  "Marketing",
  "Other",
] as const;
