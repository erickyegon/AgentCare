"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import type { WorkflowRun } from "@/lib/types";
import { Badge, Card, CardHeader, EmptyState, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

const FILTERS = ["all", "completed", "escalated", "failed", "pending"];

export default function StaffWorkflows() {
  const [filter, setFilter] = useState("all");
  const { data, isLoading } = useQuery({
    queryKey: ["staff-runs", filter],
    queryFn: () =>
      api.get<WorkflowRun[]>(`/staff/workflows${filter === "all" ? "" : `?status=${filter}`}`),
  });

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Workflows</h1>
        <div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-1">
          {FILTERS.map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`rounded-md px-3 py-1 text-sm capitalize ${filter === f ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      <Card>
        <CardHeader title="All workflow runs" />
        <div className="p-3">
          {isLoading ? <div className="p-4"><Spinner /></div> : data && data.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {data.map((r) => (
                <Link key={r.id} href={`/staff/workflows/${r.id}`} className="flex items-center justify-between gap-4 px-3 py-3 hover:bg-slate-50">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-700">{r.request_text}</p>
                    <p className="text-xs text-slate-400">run #{r.id} · {r.current_step} · {formatDateTime(r.created_at)}</p>
                  </div>
                  <Badge label={r.status} />
                </Link>
              ))}
            </div>
          ) : <div className="p-4"><EmptyState title="No workflows" /></div>}
        </div>
      </Card>
    </div>
  );
}
