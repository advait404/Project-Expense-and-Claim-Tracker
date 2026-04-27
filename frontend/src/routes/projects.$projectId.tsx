import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState, ErrorState } from "@/components/States";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { getProject, updateProject, deleteProject } from "@/api/projects";
import { getExpenses } from "@/api/expenses";
import { getIncome } from "@/api/income";
import { ApiError } from "@/api/client";
import { formatMYR, formatDate } from "@/lib/format";
import type { Project, ProjectStatus, Expense, Income } from "@/types";
import { TrendingUp, TrendingDown, Wallet } from "lucide-react";

export const Route = createFileRoute("/projects/$projectId")({
  component: ProjectDetailPage,
});

const STATUSES: { value: ProjectStatus; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "on_hold", label: "On Hold" },
  { value: "archived", label: "Archived" },
];

function ProjectDetailPage() {
  const { projectId } = Route.useParams();
  const router = useRouter();
  const navigate = router.navigate;

  const [project, setProject] = useState<Project | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [income, setIncome] = useState<Income[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [proj, exp, inc] = await Promise.all([
        getProject(projectId),
        getExpenses({ project_id: projectId }),
        getIncome(projectId),
      ]);
      setProject(proj);
      setExpenses(exp);
      setIncome(inc);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load project");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [projectId]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteProject(projectId);
      toast.success("Project deleted");
      router.navigate({ to: "/projects" });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link to="/projects" className="inline-flex">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        {project && (
          <PageHeader
            title={project.name}
            description={project.description}
          />
        )}
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && project && (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-md border bg-card p-4">
              <h3 className="text-sm font-semibold text-muted-foreground mb-2">Status</h3>
              <Badge variant="secondary" className="capitalize">
                {project.status.replace("_", " ")}
              </Badge>
            </div>
            <div className="rounded-md border bg-card p-4">
              <h3 className="text-sm font-semibold text-muted-foreground mb-2">Budget</h3>
              <p className="text-lg font-semibold">
                {project.budget != null ? formatMYR(project.budget) : "—"}
              </p>
            </div>
            <div className="rounded-md border bg-card p-4">
              <h3 className="text-sm font-semibold text-muted-foreground mb-2">Start Date</h3>
              <p className="text-sm">{project.start_date ? formatDate(project.start_date) : "—"}</p>
            </div>
            <div className="rounded-md border bg-card p-4">
              <h3 className="text-sm font-semibold text-muted-foreground mb-2">End Date</h3>
              <p className="text-sm">{project.end_date ? formatDate(project.end_date) : "—"}</p>
            </div>
          </div>

          {project.description && (
            <div className="rounded-md border bg-card p-4">
              <h3 className="text-sm font-semibold text-muted-foreground mb-2">Description</h3>
              <p className="text-sm whitespace-pre-wrap">{project.description}</p>
            </div>
          )}

          <div className="flex gap-2">
            <Button onClick={() => setEditOpen(true)}>
              <Pencil className="h-4 w-4 mr-2" /> Edit
            </Button>
            <Button variant="destructive" onClick={() => setDeleteConfirm(true)}>
              <Trash2 className="h-4 w-4 mr-2" /> Delete
            </Button>
          </div>

          {/* Summary Section */}
          <div>
            <h2 className="text-lg font-semibold mb-3">Financial Summary</h2>
            <div className="grid gap-3 md:grid-cols-3">
              <SummaryCard
                label="Total Income"
                value={income.reduce((sum, i) => sum + i.amount, 0)}
                icon={TrendingUp}
                tone="success"
              />
              <SummaryCard
                label="Total Expenses"
                value={expenses.reduce((sum, e) => sum + e.amount, 0)}
                icon={TrendingDown}
                tone="negative"
              />
              <SummaryCard
                label="Net Position"
                value={income.reduce((sum, i) => sum + i.amount, 0) - expenses.reduce((sum, e) => sum + e.amount, 0)}
                icon={Wallet}
                tone={income.reduce((sum, i) => sum + i.amount, 0) - expenses.reduce((sum, e) => sum + e.amount, 0) >= 0 ? "success" : "negative"}
              />
            </div>
          </div>

          {/* Income Section */}
          {income.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3">Income ({income.length})</h2>
              <div className="rounded-md border bg-card overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Notes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {income.map((i) => (
                      <TableRow key={i.id}>
                        <TableCell className="text-sm">{formatDate(i.date)}</TableCell>
                        <TableCell className="text-sm">{i.source}</TableCell>
                        <TableCell className="text-right text-sm font-semibold">
                          {formatMYR(i.amount)}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{i.notes || "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* Expenses Section */}
          {expenses.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3">Expenses ({expenses.length})</h2>
              <div className="rounded-md border bg-card overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Vendor</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {expenses.map((e) => (
                      <TableRow key={e.id}>
                        <TableCell className="text-sm">{formatDate(e.date)}</TableCell>
                        <TableCell className="text-sm">{e.vendor}</TableCell>
                        <TableCell className="text-sm">{e.category}</TableCell>
                        <TableCell className="text-right text-sm font-semibold">
                          {formatMYR(e.amount)}
                        </TableCell>
                        <TableCell>
                          <Badge variant={e.is_claimed ? "default" : "secondary"} className="text-xs">
                            {e.is_claimed ? "Claimed" : "Unclaimed"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {expenses.length === 0 && income.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <p>No transactions yet for this project.</p>
            </div>
          )}
        </div>
      )}

      <EditDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        project={project}
        onSaved={load}
      />

      <Dialog open={deleteConfirm} onOpenChange={setDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Project?</DialogTitle>
            <DialogDescription>
              This will permanently delete <strong>{project?.name}</strong> and all associated expenses and income.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Deleting..." : "Delete Project"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  tone?: "default" | "success" | "negative";
}) {
  const toneClass =
    tone === "success"
      ? "text-success"
      : tone === "negative"
        ? "text-destructive"
        : "text-foreground";
  return (
    <div className="rounded-md border bg-muted/30 p-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className={`text-xl font-semibold ${toneClass}`}>
        {formatMYR(value)}
      </div>
    </div>
  );
}

function EditDialog({
  open,
  onOpenChange,
  project,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  project: Project | null;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Partial<Project>>({});
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open && project) {
      setForm(project);
      setFieldErrors({});
    }
  }, [open, project]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!project) return;
    setSaving(true);
    setFieldErrors({});
    try {
      await updateProject(project.id, form);
      toast.success("Project updated");
      onOpenChange(false);
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
          <DialogTitle>Edit Project</DialogTitle>
          <DialogDescription>Update project details.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              required
              value={form.name ?? ""}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={fieldErrors.name ? "border-red-500" : ""}
            />
            {fieldErrors.name && <p className="text-sm text-red-500 mt-1">{fieldErrors.name}</p>}
          </div>
          <div>
            <Label htmlFor="desc">Description</Label>
            <Textarea
              id="desc"
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className={fieldErrors.description ? "border-red-500" : ""}
            />
            {fieldErrors.description && <p className="text-sm text-red-500 mt-1">{fieldErrors.description}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="start">Start Date</Label>
              <Input
                id="start"
                type="date"
                value={form.start_date ?? ""}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                className={fieldErrors.start_date ? "border-red-500" : ""}
              />
              {fieldErrors.start_date && <p className="text-sm text-red-500 mt-1">{fieldErrors.start_date}</p>}
            </div>
            <div>
              <Label htmlFor="end">End Date</Label>
              <Input
                id="end"
                type="date"
                value={form.end_date ?? ""}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                className={fieldErrors.end_date ? "border-red-500" : ""}
              />
              {fieldErrors.end_date && <p className="text-sm text-red-500 mt-1">{fieldErrors.end_date}</p>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="budget">Budget (MYR)</Label>
              <Input
                id="budget"
                type="number"
                step="0.01"
                value={form.budget ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    budget: e.target.value === "" ? undefined : Number(e.target.value),
                  })
                }
                className={fieldErrors.budget ? "border-red-500" : ""}
              />
              {fieldErrors.budget && <p className="text-sm text-red-500 mt-1">{fieldErrors.budget}</p>}
            </div>
            <div>
              <Label>Status</Label>
              <Select
                value={form.status}
                onValueChange={(v) => setForm({ ...form, status: v as ProjectStatus })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUSES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
