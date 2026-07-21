"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Analytics } from "@/lib/types";
import {
  ChartCard,
  ChartSkeleton,
  Datum,
  DonutChart,
  RankedBars,
  StatTile,
  statusRole,
} from "@/components/charts";
import {
  AlertTriangle,
  Bell,
  CalendarCheck,
  ClipboardList,
  FileText,
  Layers,
} from "lucide-react";

const toData = (rec: Record<string, number>, withRole = false): Datum[] =>
  Object.entries(rec).map(([label, value]) => ({
    label,
    value,
    role: withRole ? statusRole(label) : undefined,
  }));

const deptData = (d: Analytics): Datum[] =>
  d.appointments_by_department.map((x) => ({ label: x.department, value: x.count }));

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: () => api.get<Analytics>("/staff/analytics"),
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Operations analytics</h1>
        <p className="mt-1 text-sm text-slate-500">
          Computed live from the database — every figure traces to persisted records.
        </p>
      </div>

      {isLoading || !data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="skeleton h-28 rounded-2xl" />
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <ChartSkeleton />
            <ChartSkeleton />
          </div>
        </>
      ) : (
        <>
          {/* KPI hero numbers */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatTile icon={ClipboardList} label="Workflows" value={data.totals.workflows} sub={`avg ${data.totals.avg_steps_per_workflow} agent steps`} />
            <StatTile icon={CalendarCheck} label="Appointments" value={data.totals.appointments} sub={`${data.totals.reminders} reminders`} accent="var(--status-good)" />
            <StatTile icon={FileText} label="Documents" value={data.totals.documents} sub={`${data.duplicate_documents} duplicates`} accent="var(--status-info)" />
            <StatTile icon={AlertTriangle} label="Pending reviews" value={data.totals.escalations_pending} sub={`${data.totals.escalations} total escalations`} accent="var(--status-warning)" />
            <StatTile icon={Layers} label="Audit events" value={data.totals.audit_events} sub={`${data.totals.patients} patients`} accent="var(--status-neutral)" />
          </div>

          {/* Distributions */}
          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard title="Workflow status" subtitle="Share of all runs by outcome" data={toData(data.workflows_by_status, true)}>
              <DonutChart data={toData(data.workflows_by_status, true)} centerLabel="workflows" />
            </ChartCard>

            <ChartCard title="Appointments by department" subtitle="Ranked by volume" data={deptData(data)}>
              <RankedBars data={deptData(data)} />
            </ChartCard>

            <ChartCard title="Escalations by category" subtitle="Human-oversight workload" data={toData(data.escalations_by_category)}>
              <RankedBars data={toData(data.escalations_by_category)} />
            </ChartCard>

            <ChartCard title="Reminders by type" subtitle="Follow-up coverage" data={toData(data.reminders_by_type)}>
              <RankedBars data={toData(data.reminders_by_type)} />
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
}
