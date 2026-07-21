"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Appointment } from "@/lib/types";
import { Badge, Button, Card, CardHeader, EmptyState, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

export default function AppointmentsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["my-appointments"],
    queryFn: () => api.get<Appointment[]>("/me/appointments"),
  });

  const cancel = useMutation({
    mutationFn: (id: number) => api.post<Appointment>(`/me/appointments/${id}/cancel`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-appointments"] }),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">My appointments</h1>
      <Card>
        <CardHeader title="Appointments" subtitle="Booked and coordinated by the Appointment agent" />
        <div className="p-3">
          {isLoading ? (
            <div className="p-4"><Spinner /></div>
          ) : data && data.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {data.map((a) => (
                <div key={a.id} className="flex items-center justify-between gap-4 px-3 py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-700">
                      {a.confirmation_code || `Appointment #${a.id}`}
                    </p>
                    <p className="text-xs text-slate-400">{a.reason || "—"} · updated {formatDateTime(a.updated_at)}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge label={a.status} />
                    {["confirmed", "rescheduled", "pending"].includes(a.status) && (
                      <Button
                        variant="secondary"
                        className="px-2 py-1 text-xs"
                        loading={cancel.isPending && cancel.variables === a.id}
                        onClick={() => cancel.mutate(a.id)}
                      >
                        Cancel
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4"><EmptyState title="No appointments yet" hint="Submit a request to book one." /></div>
          )}
        </div>
      </Card>
    </div>
  );
}
