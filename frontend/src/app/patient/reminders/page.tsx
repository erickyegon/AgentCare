"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Reminder } from "@/lib/types";
import { Badge, Card, CardHeader, EmptyState, SkeletonRows } from "@/components/ui";
import { formatDateTime, titleCase } from "@/lib/utils";
import { Bell } from "lucide-react";

export default function RemindersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-reminders"],
    queryFn: () => api.get<Reminder[]>("/me/reminders"),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">Reminders & follow-ups</h1>
      <Card>
        <CardHeader title="Scheduled by the Follow-up agent" />
        <div className="p-3">
          {isLoading ? (
            <SkeletonRows rows={4} />
          ) : data && data.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {data.map((r) => (
                <div key={r.id} className="flex items-start justify-between gap-4 px-3 py-3">
                  <div className="flex gap-3">
                    <Bell className="mt-0.5 h-4 w-4 text-brand-500" />
                    <div>
                      <p className="text-sm text-slate-700">{r.message}</p>
                      <p className="text-xs text-slate-400">
                        {titleCase(r.reminder_type)} · {formatDateTime(r.scheduled_at)} · {r.channel}
                      </p>
                    </div>
                  </div>
                  <Badge label={r.status} />
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4"><EmptyState title="No reminders yet" /></div>
          )}
        </div>
      </Card>
    </div>
  );
}
