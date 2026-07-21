"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api, downloadReport, streamWorkflow } from "@/lib/api";
import type { TraceEvent, WorkflowRunDetail, WorkflowStep } from "@/lib/types";
import { AgentTrace } from "@/components/AgentTrace";
import { Badge, Button, Card, CardHeader, Spinner } from "@/components/ui";
import { ArrowLeft, Download } from "lucide-react";

export default function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const [liveSteps, setLiveSteps] = useState<WorkflowStep[] | null>(null);
  const [streaming, setStreaming] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["run", id],
    queryFn: () => api.get<WorkflowRunDetail>(`/workflows/${id}`),
  });

  async function runNow() {
    setStreaming(true);
    setLiveSteps([]);
    try {
      await streamWorkflow(Number(id), (evt: TraceEvent) => {
        if (evt.type === "step" && evt.event) setLiveSteps((p) => [...(p || []), evt.event as WorkflowStep]);
      });
      await refetch();
    } finally {
      setStreaming(false);
      setLiveSteps(null);
    }
  }

  if (isLoading || !data) return <div className="p-6"><Spinner /></div>;

  const steps = liveSteps ?? data.steps;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link href="/patient" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
        <ArrowLeft className="h-4 w-4" /> Back
      </Link>

      <Card>
        <CardHeader
          title={`Request #${data.id}`}
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
          {data.summary && (
            <div className="rounded-lg border border-brand-100 bg-brand-50 p-3">
              <p className="whitespace-pre-line text-sm text-slate-700">{data.summary}</p>
            </div>
          )}
          {data.status === "pending" && (
            <Button onClick={runNow} loading={streaming}>Run this workflow</Button>
          )}
        </div>
      </Card>

      {data.escalations.length > 0 && (
        <Card>
          <CardHeader title="Escalations" subtitle="Handed to the care team for human review" />
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
        <CardHeader title="Agent trace" subtitle={`${steps.length} steps`} />
        <div className="p-5">
          <AgentTrace steps={steps} live={streaming} />
        </div>
      </Card>
    </div>
  );
}
