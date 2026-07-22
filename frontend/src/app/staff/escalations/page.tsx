"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Escalation } from "@/lib/types";
import { Badge, Button, Card, CardHeader, EmptyState, Input, SkeletonRows } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

const FILTERS = ["pending", "approved", "rejected", "all"];

export default function EscalationsPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("pending");
  const [notes, setNotes] = useState<Record<number, string>>({});

  const { data, isLoading } = useQuery({
    queryKey: ["staff-escalations", filter],
    queryFn: () => api.get<Escalation[]>(`/staff/escalations?status=${filter}`),
  });

  const decide = useMutation({
    mutationFn: ({ id, approve, note }: { id: number; approve: boolean; note: string }) =>
      api.post<Escalation>(`/staff/escalations/${id}/decision`, { approve, note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["staff-escalations"] });
      qc.invalidateQueries({ queryKey: ["staff-runs"] });
    },
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Escalations</h1>
        <div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-md px-3 py-1 text-sm capitalize ${filter === f ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <Card><div className="p-2"><SkeletonRows rows={4} /></div></Card>
      ) : data && data.length > 0 ? (
        <div className="space-y-3">
          {data.map((e) => (
            <Card key={e.id}>
              <div className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold capitalize text-slate-800">{e.category.replace(/_/g, " ")}</span>
                      <Badge label={e.severity} />
                      <Badge label={e.status} />
                      {e.requires_approval && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">requires approval</span>}
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{e.reason}</p>
                    <p className="mt-1 text-xs text-slate-400">run #{e.run_id} · {formatDateTime(e.created_at)}</p>
                    {e.resolution_note && (
                      <p className="mt-2 rounded-md bg-slate-50 p-2 text-xs text-slate-500">Note: {e.resolution_note}</p>
                    )}
                  </div>
                </div>

                {e.status === "pending" && (
                  <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                    <Input
                      placeholder="Optional review note…"
                      value={notes[e.id] || ""}
                      onChange={(ev) => setNotes((n) => ({ ...n, [e.id]: ev.target.value }))}
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="success"
                        loading={decide.isPending && decide.variables?.id === e.id && decide.variables?.approve}
                        onClick={() => decide.mutate({ id: e.id, approve: true, note: notes[e.id] || "" })}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="danger"
                        loading={decide.isPending && decide.variables?.id === e.id && !decide.variables?.approve}
                        onClick={() => decide.mutate({ id: e.id, approve: false, note: notes[e.id] || "" })}
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState title={`No ${filter} escalations`} />
      )}
    </div>
  );
}
