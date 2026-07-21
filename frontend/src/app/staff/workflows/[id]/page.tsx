"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, downloadReport } from "@/lib/api";
import type { AuditEvent, WorkflowRunDetail } from "@/lib/types";
import { AgentTrace } from "@/components/AgentTrace";
import { Badge, Button, Card, CardHeader, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";
import { ArrowLeft, Download } from "lucide-react";

export default function StaffWorkflowDetail() {
  const { id } = useParams<{ id: string }>();
  const run = useQuery({ queryKey: ["run", id], queryFn: () => api.get<WorkflowRunDetail>(`/workflows/${id}`) });
  const audit = useQuery({ queryKey: ["audit", id], queryFn: () => api.get<AuditEvent[]>(`/staff/audit?workflow_run_id=${id}&limit=200`) });

  if (run.isLoading || !run.data) return <div className="p-6"><Spinner /></div>;
  const data = run.data;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Link href="/staff/workflows" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
        <ArrowLeft className="h-4 w-4" /> Back
      </Link>

      <Card>
        <CardHeader
          title={`Workflow #${data.id}`}
          subtitle={data.thread_id}
          action={
            <div className="flex items-center gap-2">
              <Badge label={data.status} />
              <Button variant="secondary" className="px-2 py-1 text-xs" onClick={() => downloadReport(data.id)}>
                <Download className="h-3.5 w-3.5" /> Report
              </Button>
            </div>
          }
        />
        <div className="space-y-3 p-5">
          <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">“{data.request_text}”</p>
          {data.summary && <p className="whitespace-pre-line rounded-lg border border-brand-100 bg-brand-50 p-3 text-sm text-slate-700">{data.summary}</p>}
          <div className="grid gap-2 text-xs text-slate-500 sm:grid-cols-3">
            <Info k="Routing" v={data.state?.routing?.department_name} />
            <Info k="Intent" v={data.state?.intent?.primary_intent} />
            <Info k="Documents" v={data.state?.documents ? `${data.state.documents.attached ?? 0} attached` : "—"} />
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Agent trace" subtitle={`${data.steps.length} steps`} />
          <div className="p-5"><AgentTrace steps={data.steps} /></div>
        </Card>

        <div className="space-y-6">
          {data.escalations.length > 0 && (
            <Card>
              <CardHeader title="Escalations" />
              <div className="space-y-2 p-5">
                {data.escalations.map((e) => (
                  <div key={e.id} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="font-medium capitalize text-amber-800">{e.category.replace(/_/g, " ")}</span>
                      <Badge label={e.status} />
                    </div>
                    <p className="mt-1 text-slate-600">{e.reason}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <CardHeader title="Audit trail" subtitle="Immutable action log for this run" />
            <div className="max-h-96 overflow-y-auto p-3 scroll-thin">
              {audit.isLoading ? <Spinner /> : (
                <div className="space-y-1">
                  {(audit.data ?? []).slice().reverse().map((a) => (
                    <div key={a.id} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-slate-50">
                      <span className="font-mono text-slate-700">{a.action}</span>
                      <span className="text-slate-400">{a.actor} · {formatDateTime(a.created_at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Info({ k, v }: { k: string; v?: string | null }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <p className="uppercase tracking-wide text-slate-400">{k}</p>
      <p className="mt-0.5 font-medium capitalize text-slate-700">{v ? String(v).replace(/_/g, " ") : "—"}</p>
    </div>
  );
}
