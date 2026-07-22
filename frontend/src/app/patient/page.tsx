"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState } from "react";
import { api, streamWorkflow } from "@/lib/api";
import type { PatientDocument, TraceEvent, WorkflowRun, WorkflowRunDetail, WorkflowStep } from "@/lib/types";
import { AgentTrace } from "@/components/AgentTrace";
import { Badge, Button, Card, CardHeader, EmptyState, SkeletonRows, Textarea } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";
import { FileUp, Send, Sparkles } from "lucide-react";

const EXAMPLES = [
  "I need a cardiology follow-up next week and want to attach my old ECG.",
  "Please book a dermatology appointment for a skin check.",
  "I want to reschedule my neurology appointment to next week.",
  "Cancel my orthopedics appointment please.",
];

export default function PatientDashboard() {
  const qc = useQueryClient();
  const [message, setMessage] = useState("");
  const [selectedDocs, setSelectedDocs] = useState<number[]>([]);
  const [liveSteps, setLiveSteps] = useState<WorkflowStep[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [finalRun, setFinalRun] = useState<WorkflowRunDetail | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const docsQuery = useQuery({
    queryKey: ["my-documents"],
    queryFn: () => api.get<PatientDocument[]>("/me/documents"),
  });
  const runsQuery = useQuery({
    queryKey: ["my-runs"],
    queryFn: () => api.get<WorkflowRun[]>("/workflows"),
  });

  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.upload<PatientDocument>("/me/documents", form);
    },
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["my-documents"] });
      setSelectedDocs((s) => [...s, doc.id]);
    },
  });

  async function submit() {
    if (message.trim().length < 3) return;
    setStreaming(true);
    setLiveSteps([]);
    setFinalRun(null);
    try {
      const run = await api.post<WorkflowRun>("/workflows", { message, document_ids: selectedDocs });
      await streamWorkflow(run.id, (evt: TraceEvent) => {
        if (evt.type === "step" && evt.event) {
          setLiveSteps((prev) => [...prev, evt.event as WorkflowStep]);
        }
      });
      const detail = await api.get<WorkflowRunDetail>(`/workflows/${run.id}`);
      setFinalRun(detail);
      setMessage("");
      setSelectedDocs([]);
      qc.invalidateQueries({ queryKey: ["my-runs"] });
      qc.invalidateQueries({ queryKey: ["my-documents"] });
    } catch {
      /* surfaced via finalRun == null */
    } finally {
      setStreaming(false);
    }
  }

  const toggleDoc = (id: number) =>
    setSelectedDocs((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Submit an administrative request</h1>
        <p className="mt-1 text-slate-500">
          Describe what you need in plain language. Our agents will coordinate it — and hand anything
          clinical or urgent to a human.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Left: request form */}
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader title="Your request" subtitle="Booking, documents, reminders, follow-up…" />
            <div className="space-y-3 p-5">
              <Textarea
                rows={4}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="e.g. I need a cardiology follow-up next week and want to attach my old ECG."
              />
              <div className="flex flex-wrap gap-1.5">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setMessage(ex)}
                    className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-500 hover:border-brand-400 hover:text-brand-600"
                  >
                    {ex.length > 42 ? ex.slice(0, 42) + "…" : ex}
                  </button>
                ))}
              </div>

              {/* Attachments */}
              <div className="rounded-lg border border-slate-200 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-700">Attach documents</span>
                  <Button variant="secondary" className="px-2 py-1 text-xs" loading={upload.isPending} onClick={() => fileRef.current?.click()}>
                    <FileUp className="h-3.5 w-3.5" /> Upload
                  </Button>
                  <input
                    ref={fileRef}
                    type="file"
                    className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); e.target.value = ""; }}
                  />
                </div>
                {docsQuery.data && docsQuery.data.length > 0 ? (
                  <div className="max-h-36 space-y-1 overflow-y-auto scroll-thin">
                    {docsQuery.data.map((d) => (
                      <label key={d.id} className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-sm hover:bg-slate-50">
                        <input type="checkbox" checked={selectedDocs.includes(d.id)} onChange={() => toggleDoc(d.id)} />
                        <span className="truncate">{d.original_filename}</span>
                        <Badge label={d.document_type} />
                        {d.is_duplicate && <span className="text-xs text-amber-600">dup</span>}
                      </label>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">No documents yet. Upload an ECG, report, or referral.</p>
                )}
              </div>

              <Button onClick={submit} loading={streaming} className="w-full">
                <Send className="h-4 w-4" /> Submit to AgentCare
              </Button>
            </div>
          </Card>
        </div>

        {/* Right: live agent trace + result */}
        <div className="lg:col-span-3">
          <Card className="min-h-[24rem]">
            <CardHeader
              title="Agent activity"
              subtitle="Live trace of each agent as it works"
              action={<Sparkles className="h-5 w-5 text-brand-500" />}
            />
            <div className="p-5">
              {!streaming && liveSteps.length === 0 && !finalRun ? (
                <EmptyState title="Your agent trace will appear here" hint="Submit a request to watch the agents coordinate in real time." />
              ) : (
                <>
                  <AgentTrace steps={liveSteps} live={streaming} />
                  {finalRun && (
                    <div className="mt-5 rounded-xl border border-brand-100 bg-brand-50 p-4">
                      <div className="mb-2 flex items-center gap-2">
                        <span className="font-semibold text-slate-800">Result</span>
                        <Badge label={finalRun.status} />
                      </div>
                      <p className="whitespace-pre-line text-sm text-slate-700">{finalRun.summary}</p>
                      <Link href={`/patient/requests/${finalRun.id}`} className="mt-3 inline-block text-sm font-medium text-brand-600">
                        View full details →
                      </Link>
                    </div>
                  )}
                </>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Recent requests */}
      <Card>
        <CardHeader title="Recent requests" />
        <div className="p-3">
          {runsQuery.isLoading ? (
            <SkeletonRows rows={3} />
          ) : runsQuery.data && runsQuery.data.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {runsQuery.data.map((run) => (
                <Link key={run.id} href={`/patient/requests/${run.id}`} className="flex items-center justify-between gap-4 px-3 py-3 hover:bg-slate-50">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-700">{run.request_text}</p>
                    <p className="text-xs text-slate-400">{formatDateTime(run.created_at)} · run #{run.id}</p>
                  </div>
                  <Badge label={run.status} />
                </Link>
              ))}
            </div>
          ) : (
            <div className="p-4"><EmptyState title="No requests yet" /></div>
          )}
        </div>
      </Card>
    </div>
  );
}
