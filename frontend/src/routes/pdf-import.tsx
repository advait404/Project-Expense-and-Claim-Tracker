import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Upload, Trash2, FileText, CheckCircle2, ArrowLeft, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState } from "@/components/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { uploadPdf, getPdfStatus, confirmPdfImport } from "@/api/pdf";
import { useProjects } from "@/hooks/useProjects";
import { EXPENSE_CATEGORIES } from "@/types";
import type { ParsedTransaction, DuplicateWarning } from "@/types";

export const Route = createFileRoute("/pdf-import")({
  component: PdfImportPage,
});

function PdfImportPage() {
  const { data: projects } = useProjects();
  const [projectId, setProjectId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [rows, setRows] = useState<ParsedTransaction[]>([]);
  const [duplicateWarning, setDuplicateWarning] = useState<DuplicateWarning | null>(null);
  const [showDuplicateDialog, setShowDuplicateDialog] = useState(false);

  const reset = () => {
    setUploadId(null);
    setRows([]);
    setFile(null);
    setDuplicateWarning(null);
    setShowDuplicateDialog(false);
  };

  const handleUpload = async () => {
    if (!file || !projectId) {
      toast.error("Select a project and a PDF file");
      return;
    }
    setUploading(true);
    try {
      const uploadRes = await uploadPdf(file);
      const newUploadId = uploadRes.upload_id;

      // Poll for status
      while (true) {
        await new Promise((r) => setTimeout(r, 2000));
        const job = await getPdfStatus(newUploadId);

        if (job.status === "done" && job.result) {
          setUploadId(newUploadId);
          setRows(job.result.parsed_transactions);
          setDuplicateWarning(job.result.duplicate_warning);

          if (job.result.duplicate_warning.is_duplicate) {
            setShowDuplicateDialog(true);
          } else {
            toast.success(`Parsed ${job.result.parsed_transactions.length} transactions`);
          }
          break;
        }

        if (job.status === "error") {
          toast.error(job.detail ?? "PDF processing failed");
          break;
        }
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const updateRow = (idx: number, patch: Partial<ParsedTransaction>) => {
    setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };

  const removeRow = (idx: number) => {
    setRows((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleConfirm = async () => {
    if (!uploadId || !projectId || rows.length === 0) return;
    setConfirming(true);
    try {
      const saved = await confirmPdfImport(uploadId, projectId, rows);
      toast.success(`Imported ${saved.length} expenses`);
      reset();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Import failed");
    } finally {
      setConfirming(false);
    }
  };

  const showReview = uploadId && rows.length >= 0;

  const handleProceedWithDuplicate = () => {
    setShowDuplicateDialog(false);
    if (uploadId && rows.length > 0) {
      toast.success(`Parsed ${rows.length} transactions (duplicate warning acknowledged)`);
    }
  };

  const handleCancelDuplicate = () => {
    reset();
  };

  return (
    <div>
      <PageHeader
        title="PDF Import"
        description="Upload a PDF, review parsed transactions, then confirm to save as expenses."
      />

      <AlertDialog open={showDuplicateDialog} onOpenChange={setShowDuplicateDialog}>
        <AlertDialogContent>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            Duplicate PDF Detected
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-3">
            <p>
              This PDF appears to be identical to a previously uploaded statement:
            </p>
            <div className="rounded-md bg-muted p-3 space-y-1 text-sm">
              <p>
                <span className="font-semibold">Filename:</span> {duplicateWarning?.previously_uploaded_filename}
              </p>
              <p>
                <span className="font-semibold">Uploaded:</span>{" "}
                {duplicateWarning?.previously_uploaded_at
                  ? new Date(duplicateWarning.previously_uploaded_at).toLocaleString()
                  : "Unknown"}
              </p>
            </div>
            <p className="text-sm">
              You can still import this PDF if the transactions haven't been imported yet. Would you like to continue?
            </p>
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelDuplicate}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleProceedWithDuplicate}>
              Continue Anyway
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {!showReview && (
        <div className="max-w-xl rounded-md border bg-card p-6 space-y-4">
          <div>
            <Label>Project</Label>
            <Select value={projectId} onValueChange={setProjectId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a project" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>PDF file</Label>
            <Input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file && (
              <p className="mt-1 text-xs text-muted-foreground inline-flex items-center gap-1">
                <FileText className="h-3 w-3" /> {file.name}
              </p>
            )}
          </div>
          <Button onClick={handleUpload} disabled={uploading || !file || !projectId}>
            <Upload className="h-4 w-4" />
            {uploading ? "Processing..." : "Upload & Parse"}
          </Button>
          {uploading && (
            <LoadingState label="Processing PDF with AI... This may take up to 2 minutes." />
          )}
        </div>
      )}

      {showReview && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={reset}>
                <ArrowLeft className="h-4 w-4" /> Cancel
              </Button>
              <span className="text-sm text-muted-foreground">
                Review {rows.length} transactions before importing.
              </span>
            </div>
            <Button onClick={handleConfirm} disabled={confirming || rows.length === 0}>
              <CheckCircle2 className="h-4 w-4" />
              {confirming ? "Importing..." : "Confirm Import"}
            </Button>
          </div>

          {rows.length === 0 ? (
            <div className="rounded-md border border-dashed p-10 text-center text-muted-foreground">
              All rows removed. Cancel to start over.
            </div>
          ) : (
            <div className="rounded-md border bg-card overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-36">Date</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-32 text-right">Amount</TableHead>
                    <TableHead className="w-24">Currency</TableHead>
                    <TableHead className="w-44">Category</TableHead>
                    <TableHead className="w-12" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <Input
                          type="date"
                          value={row.date}
                          onChange={(e) => updateRow(i, { date: e.target.value })}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          value={row.description}
                          onChange={(e) => updateRow(i, { description: e.target.value })}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          step="0.01"
                          className={`text-right font-mono ${row.amount < 0 ? "text-destructive" : ""}`}
                          value={row.amount}
                          onChange={(e) => updateRow(i, { amount: Number(e.target.value) })}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          value={row.currency}
                          onChange={(e) => updateRow(i, { currency: e.target.value })}
                        />
                      </TableCell>
                      <TableCell>
                        <Select
                          value={row.category_suggestion ?? "Other"}
                          onValueChange={(v) => updateRow(i, { category_suggestion: v })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {EXPENSE_CATEGORIES.map((c) => (
                              <SelectItem key={c} value={c}>
                                {c}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Button size="icon" variant="ghost" onClick={() => removeRow(i)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
