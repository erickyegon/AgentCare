"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditEvent } from "@/lib/types";
import { Card, CardHeader, EmptyState, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

export default function AuditPage() {
  const { data, isLoading } = useQuery({ queryKey: ["audit-all"], queryFn: () => api.get<AuditEvent[]>("/staff/audit?limit=300") });

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">Audit log</h1>
      <Card>
        <CardHeader title="Immutable action trail" subtitle="Every agent and human action is recorded" />
        <div className="p-3">
          {isLoading ? <div className="p-4"><Spinner /></div> : data && data.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Action</th>
                    <th className="px-3 py-2">Actor</th>
                    <th className="px-3 py-2">Entity</th>
                    <th className="px-3 py-2">Run</th>
                    <th className="px-3 py-2">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50">
                      <td className="px-3 py-2 font-mono text-slate-700">{a.action}</td>
                      <td className="px-3 py-2 text-slate-500">{a.actor}</td>
                      <td className="px-3 py-2 text-slate-500">{a.entity_type}{a.entity_id ? `#${a.entity_id}` : ""}</td>
                      <td className="px-3 py-2 text-slate-400">{a.workflow_run_id ?? "—"}</td>
                      <td className="px-3 py-2 text-slate-400">{formatDateTime(a.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="p-4"><EmptyState title="No audit events" /></div>}
        </div>
      </Card>
    </div>
  );
}
