"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Analytics } from "@/lib/types";
import { Card, CardHeader, Spinner } from "@/components/ui";
import { titleCase } from "@/lib/utils";
import { CalendarCheck, ClipboardList, FileText, Users } from "lucide-react";

function BarList({ data, color = "bg-brand-500" }: { data: Record<string, number>; color?: string }) {
  const entries = Object.entries(data);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  if (entries.length === 0) return <p className="p-4 text-sm text-slate-400">No data yet.</p>;
  return (
    <div className="space-y-2 p-4">
      {entries.map(([k, v]) => (
        <div key={k}>
          <div className="mb-0.5 flex justify-between text-sm">
            <span className="capitalize text-slate-600">{titleCase(k)}</span>
            <span className="font-medium text-slate-800">{v}</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div className={`h-2 rounded-full ${color}`} style={{ width: `${(v / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["analytics"], queryFn: () => api.get<Analytics>("/staff/analytics") });

  if (isLoading || !data) return <div className="p-6"><Spinner /></div>;
  const t = data.totals;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
      <p className="text-sm text-slate-500">Computed live from the database — no precomputed values.</p>

      <div className="grid gap-4 sm:grid-cols-4">
        <Stat icon={ClipboardList} label="Workflows" value={t.workflows} sub={`avg ${t.avg_steps_per_workflow} steps`} />
        <Stat icon={CalendarCheck} label="Appointments" value={t.appointments} sub={`${t.reminders} reminders`} />
        <Stat icon={FileText} label="Documents" value={t.documents} sub={`${data.duplicate_documents} duplicates`} />
        <Stat icon={Users} label="Patients" value={t.patients} sub={`${t.escalations_pending} pending reviews`} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card><CardHeader title="Workflows by status" /><BarList data={data.workflows_by_status} /></Card>
        <Card><CardHeader title="Appointments by status" /><BarList data={data.appointments_by_status} color="bg-teal-500" /></Card>
        <Card><CardHeader title="Escalations by category" /><BarList data={data.escalations_by_category} color="bg-amber-500" /></Card>
        <Card><CardHeader title="Reminders by type" /><BarList data={data.reminders_by_type} color="bg-emerald-500" /></Card>
        <Card>
          <CardHeader title="Appointments by department" />
          <BarList data={Object.fromEntries(data.appointments_by_department.map((d) => [d.department, d.count]))} color="bg-violet-500" />
        </Card>
        <Card><CardHeader title="Documents by type" /><BarList data={data.documents_by_type} color="bg-slate-500" /></Card>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, sub }: { icon: React.ComponentType<{ className?: string }>; label: string; value: number; sub?: string }) {
  return (
    <Card className="p-4">
      <Icon className="h-5 w-5 text-brand-600" />
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-sm text-slate-500">{label}</p>
      {sub && <p className="text-xs text-slate-400">{sub}</p>}
    </Card>
  );
}
