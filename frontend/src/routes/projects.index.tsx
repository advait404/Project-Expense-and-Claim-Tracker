import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
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
import {
  getProjects,
  createProject,
  updateProject,
  deleteProject,
} from "@/api/projects";
import { ApiError } from "@/api/client";
import { formatMYR, formatDate } from "@/lib/format";
import type { Project, ProjectStatus } from "@/types";

export const Route = createFileRoute("/projects/")({
  component: ProjectsListPage,
});

const STATUSES: { value: ProjectStatus; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "on_hold", label: "On Hold" },
  { value: "archived", label: "Archived" },
];

function ProjectsListPage() {
  const router = useRouter();
  const [data, setData] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Project | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getProjects());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleEdit = (p: Project) => {
    setEditing(p);
    setOpen(true);
  };

  const handleNew = () => {
    setEditing(null);
    setOpen(true);
  };

  const handleDelete = (project: Project) => {
    setDeleteConfirm(project);
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    try {
      await deleteProject(deleteConfirm.id);
      toast.success("Project and all associated expenses/income deleted");
      setDeleteConfirm(null);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Manage all your tracked projects."
        actions={
          <Button onClick={handleNew}>
            <Plus className="h-4 w-4" /> New Project
          </Button>
        }
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && data.length === 0 && (
        <EmptyState title="No projects" description="Click 'New Project' to create one." />
      )}

      {!loading && !error && data.length > 0 && (
        <div className="rounded-md border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Start</TableHead>
                <TableHead>End</TableHead>
                <TableHead className="text-right">Budget</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((p) => (
                <TableRow
                  key={p.id}
                  className="cursor-pointer hover:bg-accent"
                  onClick={() => router.navigate({ to: `/projects/${p.id}` })}
                >
                  <TableCell>
                    <div className="font-medium">{p.name}</div>
                    {p.description && (
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {p.description}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="capitalize">
                      {p.status.replace("_", " ")}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatDate(p.start_date)}</TableCell>
                  <TableCell>{formatDate(p.end_date)}</TableCell>
                  <TableCell className="text-right">
                    {p.budget != null ? formatMYR(p.budget) : "—"}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      <Button size="icon" variant="ghost" onClick={() => handleEdit(p)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => handleDelete(p)}
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

      <ProjectDialog
        open={open}
        onOpenChange={setOpen}
        project={editing}
        onSaved={() => {
          setOpen(false);
          load();
        }}
      />

      <Dialog open={!!deleteConfirm} onOpenChange={(v) => !v && setDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Project?</DialogTitle>
            <DialogDescription>
              This will permanently delete <strong>{deleteConfirm?.name}</strong> and all associated expenses and income.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting ? "Deleting..." : "Delete Project"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ProjectDialog({
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
  const [form, setForm] = useState<Partial<Project>>({
    name: "",
    description: "",
    start_date: "",
    end_date: "",
    budget: undefined,
    status: "active",
  });
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setForm(
        project ?? {
          name: "",
          description: "",
          start_date: "",
          end_date: "",
          budget: undefined,
          status: "active",
        },
      );
      setFieldErrors({});
    }
  }, [open, project]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFieldErrors({});
    try {
      if (project) {
        await updateProject(project.id, form);
        toast.success("Project updated");
      } else {
        await createProject(form);
        toast.success("Project created");
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
          <DialogTitle>{project ? "Edit Project" : "New Project"}</DialogTitle>
          <DialogDescription>
            {project ? "Update project details." : "Add a new project to track."}
          </DialogDescription>
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
