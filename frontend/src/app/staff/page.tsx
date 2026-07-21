"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Escalation, WorkflowRun } from "@/lib/types";
import { Badge, Card, CardHeader, EmptyState, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, ClipboardList } from "lucide-react";

export default function StaffOverview() {
  const runs = useQuery({ queryKey: ["staff-runs"], queryFn: () => api.get<WorkflowRun[]>("/staff/workflows") });
  const escalations = useQuery({ queryKey: ["staff-escalations", "pending"], queryFn: () => api.get<Escalation[]>("/staff/escalations?status=pending") });

  const total = runs.data?.length ?? 0;
  const completed = runs.data?.filter((r) => r.status === "completed").length ?? 0;
  const escalated = runs.data?.filter((r) => r.status === "escalated").length ?? 0;
  const pending = escalations.data?.length ?? 0;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Operations overview</h1>

      <div className="grid gap-4 sm:grid-cols-4">
        <Stat icon={ClipboardList} label="Total workflows" value={total} color="text-brand-600" />
        <Stat icon={CheckCircle2} label="Completed" value={completed} color="text-emerald-600" />
        <Stat icon={AlertTriangle} label="Escalated runs" value={escalated} color="text-amber-600" />
        <Stat icon={AlertTriangle} label="Pending review" value={pending} color="text-red-600" />
      </div>

      <Card>
        <CardHeader title="Pending escalations" subtitle="Require human review or approval" action={<Link href="/staff/escalations" className="text-sm text-brand-600">View all →</Link>} />
        <div className="p-3">
          {escalations.isLoading ? (
            <div className="p-4"><Spinner /></div>
          ) : pending > 0 ? (
            <div className="divide-y divide-slate-100">
              {escalations.data!.slice(0, 6).map((e) => (
                <div key={e.id} className="flex items-center justify-between gap-4 px-3 py-3">
                  <div>
                    <p className="text-sm font-medium capitalize text-slate-700">{e.category.replace(/_/g, " ")}</p>
                    <p className="text-xs text-slate-400">run #{e.run_id} · {formatDateTime(e.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge label={e.severity} />
                    {e.requires_approval && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">approval</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4"><EmptyState title="No pending escalations" hint="All caught up." /></div>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Recent workflows" action={<Link href="/staff/workflows" className="text-sm text-brand-600">View all →</Link>} />
        <div className="p-3">
          {runs.isLoading ? <div className="p-4"><Spinner /></div> : (
            <div className="divide-y divide-slate-100">
              {(runs.data ?? []).slice(0, 6).map((r) => (
                <Link key={r.id} href={`/staff/workflows/${r.id}`} className="flex items-center justify-between gap-4 px-3 py-3 hover:bg-slate-50">
                  <p className="truncate text-sm text-slate-700">{r.request_text}</p>
                  <Badge label={r.status} />
                </Link>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

function Stat({ icon: Icon, label, value, color }: { icon: React.ComponentType<{ className?: string }>; label: string; value: number; color: string }) {
  return (
    <Card className="p-4">
      <Icon className={`h-5 w-5 ${color}`} />
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-sm text-slate-500">{label}</p>
    </Card>
  );
}
