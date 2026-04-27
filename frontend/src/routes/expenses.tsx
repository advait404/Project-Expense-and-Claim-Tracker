import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Plus, Pencil, Trash2, FileText, PencilLine } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  getExpenses,
  createExpense,
  updateExpense,
  deleteExpense,
  bulkToggleClaim,
  type ExpenseFilters,
} from "@/api/expenses";
import { ApiError } from "@/api/client";
import { useProjects } from "@/hooks/useProjects";
import { EXPENSE_CATEGORIES } from "@/types";
import type { Expense } from "@/types";
import { formatMYR, formatDate } from "@/lib/format";

export const Route = createFileRoute("/expenses")({
  component: ExpensesPage,
});

const ALL = "__all__";

function ExpensesPage() {
  const { data: projects } = useProjects();
  const [filters, setFilters] = useState<ExpenseFilters>({});
  const [data, setData] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getExpenses(filters));
      setSelectedIds(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load expenses");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)]);

  const projectName = useMemo(() => {
    const m = new Map(projects.map((p) => [p.id, p.name]));
    return (id: string) => m.get(id) ?? id;
  }, [projects]);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this expense?")) return;
    try {
      await deleteExpense(id);
      toast.success("Deleted");
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleBulkClaim = async (is_claimed: boolean) => {
    setBulkLoading(true);
    try {
      await bulkToggleClaim([...selectedIds], is_claimed);
      toast.success(is_claimed ? "Marked as claimed" : "Marked as unclaimed");
      setSelectedIds(new Set());
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Bulk update failed");
    } finally {
      setBulkLoading(false);
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === data.length && data.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.map((e) => e.id)));
    }
  };

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  return (
    <div>
      <PageHeader
        title="Expenses"
        description="All expenses across projects. Toggle claimed status inline."
        actions={
          <div className="flex items-center gap-2">
            {selectedIds.size > 0 && (
              <>
                <span className="text-sm text-muted-foreground">{selectedIds.size} selected</span>
                <Button
                  variant="outline"
                  disabled={bulkLoading}
                  onClick={() => handleBulkClaim(true)}
                >
                  Claim Selected
                </Button>
                <Button
                  variant="outline"
                  disabled={bulkLoading}
                  onClick={() => handleBulkClaim(false)}
                >
                  Unclaim Selected
                </Button>
              </>
            )}
            <Button
              onClick={() => {
                setEditing(null);
                setOpen(true);
              }}
            >
              <Plus className="h-4 w-4" /> New Expense
            </Button>
          </div>
        }
      />

      {/* Filters */}
      <div className="grid gap-3 mb-4 md:grid-cols-5">
        <div>
          <Label className="text-xs">Project</Label>
          <Select
            value={filters.project_id ?? ALL}
            onValueChange={(v) =>
              setFilters((f) => ({ ...f, project_id: v === ALL ? undefined : v }))
            }
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
        <div>
          <Label className="text-xs">Category</Label>
          <Select
            value={filters.category ?? ALL}
            onValueChange={(v) =>
              setFilters((f) => ({ ...f, category: v === ALL ? undefined : v }))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="All" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All categories</SelectItem>
              {EXPENSE_CATEGORIES.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs">From</Label>
          <Input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, date_from: e.target.value || undefined }))
            }
          />
        </div>
        <div>
          <Label className="text-xs">To</Label>
          <Input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, date_to: e.target.value || undefined }))
            }
          />
        </div>
        <div>
          <Label className="text-xs">Claim Status</Label>
          <Select
            value={
              filters.is_claimed === undefined ? ALL : filters.is_claimed ? "yes" : "no"
            }
            onValueChange={(v) =>
              setFilters((f) => ({
                ...f,
                is_claimed: v === ALL ? undefined : v === "yes",
              }))
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All</SelectItem>
              <SelectItem value="yes">Claimed</SelectItem>
              <SelectItem value="no">Unclaimed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && data.length === 0 && (
        <EmptyState title="No expenses found" description="Try changing filters or add a new expense." />
      )}

      {!loading && !error && data.length > 0 && (
        <div className="rounded-md border bg-card overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <Checkbox
                    checked={selectedIds.size === data.length && data.length > 0}
                    onCheckedChange={toggleSelectAll}
                  />
                </TableHead>
                <TableHead>Project</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Vendor / Description</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Currency Conversion</TableHead>
                <TableHead>Claimed</TableHead>
                <TableHead>Claimed Date</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((exp) => {
                const negative = exp.amount < 0;
                return (
                  <TableRow key={exp.id}>
                    <TableCell className="w-10">
                      <Checkbox
                        checked={selectedIds.has(exp.id)}
                        onCheckedChange={() => toggleSelect(exp.id)}
                      />
                    </TableCell>
                    <TableCell className="text-sm">
                      {exp.project_name ?? projectName(exp.project_id)}
                    </TableCell>
                    <TableCell className="text-sm">{formatDate(exp.date)}</TableCell>
                    <TableCell>
                      <div className="font-medium">{exp.vendor}</div>
                      {exp.description && (
                        <div className="text-xs text-muted-foreground line-clamp-1">
                          {exp.description}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{exp.category}</Badge>
                    </TableCell>
                    <TableCell
                      className={`text-right font-mono ${negative ? "text-destructive" : ""}`}
                    >
                      {formatMYR(exp.amount)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="gap-1">
                        {exp.source === "pdf" ? (
                          <FileText className="h-3 w-3" />
                        ) : (
                          <PencilLine className="h-3 w-3" />
                        )}
                        {exp.source}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {exp.currency_conversion_type ? (
                        <Badge
                          variant={
                            exp.currency_conversion_type === "native"
                              ? "outline"
                              : "secondary"
                          }
                        >
                          {exp.currency_conversion_type === "native"
                            ? "No"
                            : "Yes"}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {exp.is_claimed ? (
                        <Badge className="bg-success text-success-foreground hover:bg-success/90">
                          Claimed
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="border-warning text-warning">
                          Unclaimed
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {exp.is_claimed && exp.claimed_date ? formatDate(exp.claimed_date) : "-"}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            setEditing(exp);
                            setOpen(true);
                          }}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleDelete(exp.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <ExpenseDialog
        open={open}
        onOpenChange={setOpen}
        expense={editing}
        onSaved={() => {
          setOpen(false);
          load();
        }}
      />
    </div>
  );
}

function ExpenseDialog({
  open,
  onOpenChange,
  expense,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  expense: Expense | null;
  onSaved: () => void;
}) {
  const { data: projects } = useProjects();
  const [form, setForm] = useState<Partial<Expense>>({
    project_id: "",
    date: new Date().toISOString().slice(0, 10),
    vendor: "",
    description: "",
    amount: 0,
    currency: "MYR",
    category: "Other",
    is_claimed: false,
    claimed_date: null,
    notes: "",
    source: "manual",
    currency_conversion_type: "native",
    original_value: null,
    original_currency: null,
    fx_rate: null,
    fx_rate_timestamp: null,
  });
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setForm(
        expense ?? {
          project_id: projects[0]?.id ?? "",
          date: new Date().toISOString().slice(0, 10),
          vendor: "",
          description: "",
          amount: 0,
          currency: "MYR",
          category: "Other",
          is_claimed: false,
          claimed_date: null,
          notes: "",
          source: "manual",
          currency_conversion_type: "native",
          original_value: null,
          original_currency: null,
          fx_rate: null,
          fx_rate_timestamp: null,
        },
      );
      setFieldErrors({});
    }
  }, [open, expense, projects]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFieldErrors({});
    try {
      if (expense) {
        await updateExpense(expense.id, form);
        toast.success("Expense updated");
      } else {
        await createExpense({ ...form, source: "manual" });
        toast.success("Expense created");
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{expense ? "Edit Expense" : "New Expense"}</DialogTitle>
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
            <Label>Vendor</Label>
            <Input
              required
              value={form.vendor ?? ""}
              onChange={(e) => setForm({ ...form, vendor: e.target.value })}
              className={fieldErrors.vendor ? "border-red-500" : ""}
            />
            {fieldErrors.vendor && <p className="text-sm text-red-500 mt-1">{fieldErrors.vendor}</p>}
          </div>
          <div>
            <Label>Description</Label>
            <Input
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className={fieldErrors.description ? "border-red-500" : ""}
            />
            {fieldErrors.description && <p className="text-sm text-red-500 mt-1">{fieldErrors.description}</p>}
          </div>
          <div className="grid grid-cols-3 gap-3">
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
            <div>
              <Label>Category</Label>
              <Select
                value={form.category}
                onValueChange={(v) => setForm({ ...form, category: v })}
              >
                <SelectTrigger className={fieldErrors.category ? "border-red-500" : ""}>
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
              {fieldErrors.category && <p className="text-sm text-red-500 mt-1">{fieldErrors.category}</p>}
            </div>
          </div>
          <div>
            <Label>Currency Conversion Type</Label>
            <Select
              value={form.currency_conversion_type ?? "native"}
              onValueChange={(v) =>
                setForm({ ...form, currency_conversion_type: v as "native" | "converted_by_bank" })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="native">Native (MYR)</SelectItem>
                <SelectItem value="converted_by_bank">Converted by Bank</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {form.currency_conversion_type === "converted_by_bank" && (
            <div className="space-y-3 rounded-md bg-secondary/30 p-3">
              <div className="text-sm font-medium">Conversion Details</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Original Currency</Label>
                  <Input
                    value={form.original_currency ?? ""}
                    placeholder="e.g., USD"
                    onChange={(e) =>
                      setForm({ ...form, original_currency: e.target.value || null })
                    }
                  />
                </div>
                <div>
                  <Label>Original Value</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={form.original_value ?? ""}
                    placeholder="e.g., 95.20"
                    onChange={(e) =>
                      setForm({
                        ...form,
                        original_value: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                  />
                </div>
              </div>
              <div>
                <Label>Exchange Rate (FX Rate)</Label>
                <Input
                  type="number"
                  step="0.0001"
                  value={form.fx_rate ?? ""}
                  placeholder="e.g., 4.723"
                  onChange={(e) =>
                    setForm({
                      ...form,
                      fx_rate: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                />
              </div>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Switch
              checked={form.is_claimed ?? false}
              onCheckedChange={(v) => setForm({ ...form, is_claimed: v })}
              id="claimed"
            />
            <Label htmlFor="claimed">Marked as claimed</Label>
          </div>
          {form.is_claimed && (
            <div>
              <Label>Claimed Date</Label>
              <Input
                type="date"
                value={form.claimed_date ?? ""}
                onChange={(e) => setForm({ ...form, claimed_date: e.target.value || null })}
              />
            </div>
          )}
          <div>
            <Label>Notes</Label>
            <Textarea
              value={form.notes ?? ""}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
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
