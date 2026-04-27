import { apiRequest } from "./client";
import type { Expense } from "@/types";

export interface ExpenseFilters {
  project_id?: string;
  date_from?: string;
  date_to?: string;
  category?: string;
  is_claimed?: boolean;
}

// TODO: connect to backend endpoint: GET /api/expenses
export const getExpenses = (filters: ExpenseFilters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "" && v !== null) params.append(k, String(v));
  });
  const qs = params.toString();
  return apiRequest<Expense[]>(`/expenses${qs ? `?${qs}` : ""}`);
};

// TODO: connect to backend endpoint: POST /api/expenses
export const createExpense = (data: Partial<Expense>) =>
  apiRequest<Expense>("/expenses", "POST", data);

// TODO: connect to backend endpoint: PUT /api/expenses/:id
export const updateExpense = (id: string, data: Partial<Expense>) =>
  apiRequest<Expense>(`/expenses/${id}`, "PUT", data);

// TODO: connect to backend endpoint: DELETE /api/expenses/:id
export const deleteExpense = (id: string) =>
  apiRequest<void>(`/expenses/${id}`, "DELETE");

// TODO: connect to backend endpoint: PATCH /api/expenses/:id/claim-toggle
export const toggleExpenseClaim = (id: string) =>
  apiRequest<Expense>(`/expenses/${id}/claim-toggle`, "PATCH");

// TODO: connect to backend endpoint: PATCH /api/expenses/bulk-claim-toggle
export const bulkToggleClaim = (ids: string[], is_claimed: boolean) =>
  apiRequest<Expense[]>("/expenses/bulk-claim-toggle", "PATCH", { ids, is_claimed });
