import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  getIncome,
  createIncome,
  updateIncome,
  deleteIncome,
} from "@/api/income";
import { ApiError } from "@/api/client";
import { useProjects } from "@/hooks/useProjects";
import type { Income } from "@/types";
import { formatMYR, formatDate } from "@/lib/format";

export const Route = createFileRoute("/income")({
  component: IncomePage,
});

const ALL = "__all__";

function IncomePage() {
  const { data: projects } = useProjects();
  const [projectId, setProjectId] = useState<string | undefined>(undefined);
  const [data, setData] = useState<Income[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Income | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getIncome(projectId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load income");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const projectName = useMemo(() => {
    const m = new Map(projects.map((p) => [p.id, p.name]));
    return (id: string) => m.get(id) ?? id;
  }, [projects]);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this income entry?")) return;
    try {
      await deleteIncome(id);
      toast.success("Deleted");
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div>
      <PageHeader
        title="Income"
        description="Manually entered income per project. Income is never derived from PDF."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Plus className="h-4 w-4" /> New Income
          </Button>
        }
      />

      <div className="grid gap-3 mb-4 md:grid-cols-3">
        <div>
          <Label className="text-xs">Project</Label>
          <Select
            value={projectId ?? ALL}
            onValueChange={(v) => setProjectId(v === ALL ? undefined : v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="All" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All projects</SelectItem>
              {projects.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && data.length === 0 && (
        <EmptyState title="No income entries" description="Add your first income entry." />
      )}

      {!loading && !error && data.length > 0 && (
        <div className="rounded-md border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Project</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Source</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((inc) => (
                <TableRow key={inc.id}>
                  <TableCell className="text-sm">
                    {inc.project_name ?? projectName(inc.project_id)}
                  </TableCell>
                  <TableCell className="text-sm">{formatDate(inc.date)}</TableCell>
                  <TableCell className="font-medium">{inc.source}</TableCell>
                  <TableCell
                    className={`text-right font-mono ${inc.amount < 0 ? "text-destructive" : "text-success"}`}
                  >
                    {formatMYR(inc.amount)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground line-clamp-1">
                    {inc.notes ?? ""}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => {
                          setEditing(inc);
                          setOpen(true);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => handleDelete(inc.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <IncomeDialog
        open={open}
        onOpenChange={setOpen}
        income={editing}
        onSaved={() => {
          setOpen(false);
          load();
        }}
      />
    </div>
  );
}

function IncomeDialog({
  open,
  onOpenChange,
  income,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  income: Income | null;
  onSaved: () => void;
}) {
  const { data: projects } = useProjects();
  const [form, setForm] = useState<Partial<Income>>({
    project_id: "",
    date: new Date().toISOString().slice(0, 10),
    source: "",
    amount: 0,
    currency: "MYR",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setForm(
        income ?? {
          project_id: projects[0]?.id ?? "",
          date: new Date().toISOString().slice(0, 10),
          source: "",
          amount: 0,
          currency: "MYR",
          notes: "",
        },
      );
      setFieldErrors({});
    }
  }, [open, income, projects]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFieldErrors({});
    try {
      if (income) {
        await updateIncome(income.id, form);
        toast.success("Income updated");
      } else {
        await createIncome(form);
        toast.success("Income created");
      }
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && err.errors) {
        const errors: Record<string, string> = {};
        err.errors.forEach((e) => {
          errors[e.field] = e.message;
        });
        setFieldErrors(errors);
        toast.error("Please fix the validation errors");
      } else {
        toast.error(err instanceof Error ? err.message : "Save failed");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{income ? "Edit Income" : "New Income"}</DialogTitle>
          <DialogDescription>Income is always entered manually.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Project</Label>
              <Select
                value={form.project_id}
                onValueChange={(v) => setForm({ ...form, project_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select project" />
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
              <Label>Date</Label>
              <Input
                type="date"
                required
                value={form.date ?? ""}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                className={fieldErrors.date ? "border-red-500" : ""}
              />
              {fieldErrors.date && <p className="text-sm text-red-500 mt-1">{fieldErrors.date}</p>}
            </div>
          </div>
          <div>
            <Label>Source</Label>
            <Input
              required
              placeholder="e.g. Client invoice, Grant"
              value={form.source ?? ""}
              onChange={(e) => setForm({ ...form, source: e.target.value })}
              className={fieldErrors.source ? "border-red-500" : ""}
            />
            {fieldErrors.source && <p className="text-sm text-red-500 mt-1">{fieldErrors.source}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Amount</Label>
              <Input
                type="number"
                step="0.01"
                required
                value={form.amount ?? 0}
                onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
                className={fieldErrors.amount ? "border-red-500" : ""}
              />
              {fieldErrors.amount && <p className="text-sm text-red-500 mt-1">{fieldErrors.amount}</p>}
            </div>
            <div>
              <Label>Currency</Label>
              <Input
                value={form.currency ?? "MYR"}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
                className={fieldErrors.currency ? "border-red-500" : ""}
              />
              {fieldErrors.currency && <p className="text-sm text-red-500 mt-1">{fieldErrors.currency}</p>}
            </div>
          </div>
          <div>
            <Label>Notes</Label>
            <Textarea
              value={form.notes ?? ""}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className={fieldErrors.notes ? "border-red-500" : ""}
            />
            {fieldErrors.notes && <p className="text-sm text-red-500 mt-1">{fieldErrors.notes}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || !form.project_id}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
