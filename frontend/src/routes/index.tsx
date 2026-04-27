import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  CheckCircle2,
  Circle,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getProjectsSummary } from "@/api/projects";
import { getExpenses } from "@/api/expenses";
import { formatMYR } from "@/lib/format";
import type { ProjectSummary, Expense } from "@/types";

export const Route = createFileRoute("/")({
  component: DashboardPage,
});

function StatCell({
  label,
  value,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  tone?: "default" | "positive" | "negative" | "warning" | "success";
}) {
  const toneClass =
    tone === "positive" || tone === "success"
      ? "text-success"
      : tone === "negative"
        ? "text-destructive"
        : tone === "warning"
          ? "text-warning"
          : "text-foreground";
  return (
    <div className="rounded-md border bg-muted/30 p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className={`mt-1 text-base font-semibold ${toneClass}`}>
        {formatMYR(value)}
      </div>
    </div>
  );
}

function CategoryBreakdown({
  rows,
}: {
  rows: { category: string; amount: number; pct: number; claimed: number; unclaimed: number }[];
}) {
  if (rows.length === 0) return null;
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
          Expenses by Category
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {rows.map(({ category, amount, pct, claimed, unclaimed }) => {
          const claimedPct = amount > 0 ? (claimed / amount) * 100 : 0;
          const unclaimedPct = amount > 0 ? (unclaimed / amount) * 100 : 0;
          return (
            <div key={category}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium">{category}</span>
                <span className="text-sm text-muted-foreground tabular-nums">
                  {formatMYR(amount)}{" "}
                  <span className="text-xs">({pct.toFixed(1)}% of total)</span>
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-muted overflow-hidden mb-2 flex">
                {claimedPct > 0 && (
                  <div
                    className="h-full bg-success transition-all"
                    style={{ width: `${claimedPct}%` }}
                  />
                )}
                {unclaimedPct > 0 && (
                  <div
                    className="h-full bg-warning transition-all"
                    style={{ width: `${unclaimedPct}%` }}
                  />
                )}
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <span className="inline-block h-1.5 w-1.5 rounded-sm bg-success" />
                  <span>{formatMYR(claimed)}</span>
                  <span>({claimedPct.toFixed(0)}%)</span>
                </div>
                <span>•</span>
                <div className="flex items-center gap-1">
                  <span className="inline-block h-1.5 w-1.5 rounded-sm bg-warning" />
                  <span>{formatMYR(unclaimed)}</span>
                  <span>({unclaimedPct.toFixed(0)}%)</span>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function DashboardPage() {
  const [data, setData] = useState<ProjectSummary[]>([]);
  const [summariesLoading, setSummariesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [expensesLoading, setExpensesLoading] = useState(true);
  const [expensesError, setExpensesError] = useState<string | null>(null);

  const loading = summariesLoading || expensesLoading;

  const loadSummaries = async () => {
    setSummariesLoading(true);
    setError(null);
    try {
      setData(await getProjectsSummary());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load summary");
    } finally {
      setSummariesLoading(false);
    }
  };

  const loadExpenses = async () => {
    setExpensesLoading(true);
    setExpensesError(null);
    try {
      setExpenses(await getExpenses());
    } catch (e) {
      setExpensesError(e instanceof Error ? e.message : "Failed to load expenses");
    } finally {
      setExpensesLoading(false);
    }
  };

  const loadAll = () => {
    loadSummaries();
    loadExpenses();
  };

  useEffect(() => {
    loadAll();
  }, []);

  const totals = data.reduce(
    (acc, p) => {
      acc.income += p.total_income;
      acc.expenses += p.total_expenses;
      acc.net += p.net_position;
      acc.claimed += p.total_claimed;
      acc.unclaimed += p.total_unclaimed;
      return acc;
    },
    { income: 0, expenses: 0, net: 0, claimed: 0, unclaimed: 0 },
  );

  const categoryTotals = useMemo(() => {
    if (expenses.length === 0) return [];
    const map = new Map<
      string,
      { amount: number; claimed: number; unclaimed: number }
    >();
    for (const exp of expenses) {
      const existing = map.get(exp.category) || {
        amount: 0,
        claimed: 0,
        unclaimed: 0,
      };
      existing.amount += exp.amount;
      if (exp.is_claimed) {
        existing.claimed += exp.amount;
      } else {
        existing.unclaimed += exp.amount;
      }
      map.set(exp.category, existing);
    }
    const totalExpenses = [...map.values()].reduce((a, b) => a + b.amount, 0);
    return [...map.entries()]
      .map(([category, { amount, claimed, unclaimed }]) => ({
        category,
        amount,
        claimed,
        unclaimed,
        pct: totalExpenses > 0 ? (amount / totalExpenses) * 100 : 0,
      }))
      .sort((a, b) => b.amount - a.amount);
  }, [expenses]);

  const projectTopCategories = useMemo(() => {
    const byProject = new Map<string, Map<string, number>>();
    for (const exp of expenses) {
      const pid = String(exp.project_id);
      if (!byProject.has(pid)) byProject.set(pid, new Map());
      const catMap = byProject.get(pid)!;
      catMap.set(exp.category, (catMap.get(exp.category) ?? 0) + exp.amount);
    }
    const result = new Map<string, string[]>();
    for (const [pid, catMap] of byProject.entries()) {
      const sorted = [...catMap.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([cat]) => cat);
      result.set(pid, sorted);
    }
    return result;
  }, [expenses]);


  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Financial summary across all projects (MYR)."
      />

      {/* Totals */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5 mb-6">
        <StatCell label="Total Income" value={totals.income} icon={TrendingUp} tone="success" />
        <StatCell label="Total Expenses" value={totals.expenses} icon={TrendingDown} tone="negative" />
        <StatCell
          label="Net Position"
          value={totals.net}
          icon={Wallet}
          tone={totals.net >= 0 ? "success" : "negative"}
        />
        <StatCell label="Claimed" value={totals.claimed} icon={CheckCircle2} tone="default" />
        <StatCell label="Unclaimed" value={totals.unclaimed} icon={Circle} tone="warning" />
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={loadAll} />}
      {!loading && !error && data.length === 0 && (
        <EmptyState
          title="No projects yet"
          description="Create a project to start tracking expenses and income."
        />
      )}

      {/* Breakdown section */}
      {!expensesLoading && !expensesError && expenses.length > 0 && (
        <div className="mb-6">
          <CategoryBreakdown rows={categoryTotals} />
        </div>
      )}

      {/* Expenses error shown inline (non-fatal) */}
      {expensesError && (
        <ErrorState message={expensesError} onRetry={loadAll} />
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.map((p) => (
          <Card key={p.project_id} className="hover:shadow-sm transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-base">
                  <Link
                    to="/projects"
                    className="hover:underline"
                  >
                    {p.project_name}
                  </Link>
                </CardTitle>
                <Badge
                  variant={p.net_position >= 0 ? "default" : "destructive"}
                  className={p.net_position >= 0 ? "bg-success text-success-foreground hover:bg-success/90" : ""}
                >
                  Net {formatMYR(p.net_position)}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-2">
                <StatCell label="Income" value={p.total_income} icon={TrendingUp} tone="success" />
                <StatCell label="Expenses" value={p.total_expenses} icon={TrendingDown} tone="negative" />
                <StatCell label="Claimed" value={p.total_claimed} icon={CheckCircle2} />
                <StatCell label="Unclaimed" value={p.total_unclaimed} icon={Circle} tone="warning" />
              </div>
              {(() => {
                const cats = projectTopCategories.get(String(p.project_id));
                return cats && cats.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {cats.map((cat) => (
                      <Badge key={cat} variant="outline" className="text-xs">
                        {cat}
                      </Badge>
                    ))}
                  </div>
                ) : null;
              })()}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
