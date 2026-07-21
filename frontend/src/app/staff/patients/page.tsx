"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";
import { Card, CardHeader, EmptyState, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";

export default function StaffPatients() {
  const { data, isLoading } = useQuery({ queryKey: ["staff-patients"], queryFn: () => api.get<Me[]>("/staff/patients") });

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">Patients</h1>
      <Card>
        <CardHeader title="Registered patients" subtitle="Synthetic demonstration data" />
        <div className="p-3">
          {isLoading ? <div className="p-4"><Spinner /></div> : data && data.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {data.map((p) => (
                <div key={p.id} className="flex items-center justify-between gap-4 px-3 py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-700">{p.name}</p>
                    <p className="text-xs text-slate-400">{p.email} · MRN {p.profile?.mrn || "—"}</p>
                  </div>
                  <span className="text-xs text-slate-400">joined {formatDateTime(p.created_at)}</span>
                </div>
              ))}
            </div>
          ) : <div className="p-4"><EmptyState title="No patients" /></div>}
        </div>
      </Card>
    </div>
  );
}
