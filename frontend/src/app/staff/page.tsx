"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Escalation, WorkflowRun } from "@/lib/types";
import { Badge, Card, CardHeader, EmptyState, SkeletonRows, SkeletonTiles } from "@/components/ui";
import {
  AgentPipeline,
  DonutChart,
  StatTile,
  statusRole,
  type Datum,
} from "@/components/charts";
import { formatDateTime } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, ClipboardList, Clock } from "lucide-react";

export default function StaffOverview() {
  const runs = useQuery({ queryKey: ["staff-runs"], queryFn: () => api.get<WorkflowRun[]>("/staff/workflows") });
  const escalations = useQuery({
    queryKey: ["staff-escalations", "pending"],
    queryFn: () => api.get<Escalation[]>("/staff/escalations?status=pending"),
  });

  const runList = runs.data ?? [];
  const total = runList.length;
  const completed = runList.filter((r) => r.status === "completed").length;
  const escalated = runList.filter((r) => r.status === "escalated").length;
  const pending = escalations.data?.length ?? 0;

  // Status distribution for the donut.
  const byStatus: Record<string, number> = {};
  for (const r of runList) byStatus[r.status] = (byStatus[r.status] || 0) + 1;
  const donutData: Datum[] = Object.entries(byStatus).map(([label, value]) => ({
    label,
    value,
    role: statusRole(label),
  }));

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Operations overview</h1>
        <p className="mt-1 text-sm text-slate-500">A live snapshot of coordination activity and human-review workload.</p>
      </div>

      {/* Agent pipeline explainer */}
      <Card className="p-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-400">Coordination pipeline</p>
        <AgentPipeline />
      </Card>

      {/* KPIs */}
      {runs.isLoading ? (
        <SkeletonTiles count={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile icon={ClipboardList} label="Total workflows" value={total} sub="all time" />
          <StatTile icon={CheckCircle2} label="Completed" value={completed} sub={total ? `${Math.round((completed / total) * 100)}% of runs` : "—"} accent="var(--status-good)" />
          <StatTile icon={AlertTriangle} label="Escalated runs" value={escalated} sub="handed to humans" accent="var(--status-warning)" />
          <StatTile icon={Clock} label="Pending review" value={pending} sub="awaiting a decision" accent="var(--status-critical)" />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Status donut */}
        <Card>
          <CardHeader title="Workflow status" subtitle="Share of all runs by outcome" />
          <div className="p-5">
            {runs.isLoading ? <div className="skeleton h-36 rounded-xl" /> : <DonutChart data={donutData} centerLabel="workflows" />}
          </div>
        </Card>

        {/* Pending escalations */}
        <Card>
          <CardHeader
            title="Pending escalations"
            subtitle="Require human review or approval"
            action={<Link href="/staff/escalations" className="text-sm text-brand-600">View all →</Link>}
          />
          <div className="p-3">
            {escalations.isLoading ? (
              <SkeletonRows rows={4} />
            ) : pending > 0 ? (
              <div className="divide-y divide-slate-100">
                {escalations.data!.slice(0, 5).map((e) => (
                  <Link key={e.id} href="/staff/escalations" className="flex items-center justify-between gap-4 px-3 py-3 hover:bg-slate-50">
                    <div>
                      <p className="text-sm font-medium capitalize text-slate-700">{e.category.replace(/_/g, " ")}</p>
                      <p className="text-xs text-slate-400">run #{e.run_id} · {formatDateTime(e.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge label={e.severity} />
                      {e.requires_approval && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">approval</span>}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-4"><EmptyState title="No pending escalations" hint="All caught up." /></div>
            )}
          </div>
        </Card>
      </div>

      {/* Recent workflows */}
      <Card>
        <CardHeader title="Recent workflows" action={<Link href="/staff/workflows" className="text-sm text-brand-600">View all →</Link>} />
        <div className="p-3">
          {runs.isLoading ? (
            <SkeletonRows rows={6} />
          ) : total > 0 ? (
            <div className="divide-y divide-slate-100">
              {runList.slice(0, 6).map((r) => (
                <Link key={r.id} href={`/staff/workflows/${r.id}`} className="flex items-center justify-between gap-4 px-3 py-3 hover:bg-slate-50">
                  <p className="truncate text-sm text-slate-700">{r.request_text}</p>
                  <Badge label={r.status} />
                </Link>
              ))}
            </div>
          ) : (
            <div className="p-4"><EmptyState title="No workflows yet" /></div>
          )}
        </div>
      </Card>
    </div>
  );
}
