import { apiRequest } from "./client";
import type { Income } from "@/types";

// TODO: connect to backend endpoint: GET /api/income?project_id=
export const getIncome = (project_id?: string) => {
  const qs = project_id ? `?project_id=${encodeURIComponent(project_id)}` : "";
  return apiRequest<Income[]>(`/income${qs}`);
};

// TODO: connect to backend endpoint: POST /api/income
export const createIncome = (data: Partial<Income>) =>
  apiRequest<Income>("/income", "POST", data);

// TODO: connect to backend endpoint: PUT /api/income/:id
export const updateIncome = (id: string, data: Partial<Income>) =>
  apiRequest<Income>(`/income/${id}`, "PUT", data);

// TODO: connect to backend endpoint: DELETE /api/income/:id
export const deleteIncome = (id: string) =>
  apiRequest<void>(`/income/${id}`, "DELETE");
