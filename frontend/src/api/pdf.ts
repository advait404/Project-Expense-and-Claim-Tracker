import { apiRequest, apiUpload } from "./client";
import type { Expense, ParsedTransaction, PdfJobStatus, PdfUploadResponse } from "@/types";

export const uploadPdf = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return apiUpload<{ upload_id: string; status: string }>("/pdf/upload", fd);
};

export const getPdfStatus = (upload_id: string) =>
  apiRequest<PdfJobStatus>(`/pdf/status/${upload_id}`, "GET");

export const confirmPdfImport = (
  upload_id: string,
  project_id: string,
  transactions: ParsedTransaction[],
) =>
  apiRequest<Expense[]>("/pdf/confirm", "POST", {
    upload_id,
    project_id,
    transactions,
  });
