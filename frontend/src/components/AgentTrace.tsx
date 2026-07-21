"use client";

import type { WorkflowStep } from "@/lib/types";
import { AGENT_META, cn, formatDateTime, titleCase } from "@/lib/utils";
import { Badge } from "./ui";
import { CheckCircle2, Loader2 } from "lucide-react";

export function AgentTrace({ steps, live }: { steps: WorkflowStep[]; live?: boolean }) {
  if (steps.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-slate-400">
        {live ? "Waiting for the agents to start…" : "No agent activity recorded."}
      </div>
    );
  }

  return (
    <ol className="relative space-y-4 pl-6">
      <span className="absolute left-[9px] top-2 h-[calc(100%-1rem)] w-px bg-slate-200" aria-hidden />
      {steps.map((step) => {
        const meta = AGENT_META[step.agent] || { label: titleCase(step.agent), color: "bg-slate-100 text-slate-700", icon: "•" };
        const halted = step.status === "halted" || step.status === "failed";
        const escalated = step.status === "escalated";
        return (
          <li key={`${step.sequence}-${step.id}`} className="relative animate-fade-in">
            <span
              className={cn(
                "absolute -left-6 top-1 grid h-5 w-5 place-items-center rounded-full text-[11px]",
                halted ? "bg-red-100" : escalated ? "bg-amber-100" : "bg-emerald-100",
              )}
            >
              {halted ? "!" : escalated ? "⚠" : <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />}
            </span>
            <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold", meta.color)}>
                  <span>{meta.icon}</span> {meta.label} Agent
                </span>
                <div className="flex items-center gap-2">
                  <Badge label={step.status} />
                  <span className="text-xs text-slate-400">{formatDateTime(step.created_at)}</span>
                </div>
              </div>
              <p className="mt-2 text-sm text-slate-700">{step.message}</p>
              <p className="mt-1 text-xs uppercase tracking-wide text-slate-400">{titleCase(step.action)}</p>
            </div>
          </li>
        );
      })}
      {live && (
        <li className="relative">
          <span className="absolute -left-6 top-1 grid h-5 w-5 place-items-center rounded-full bg-brand-100">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-600" />
          </span>
          <p className="pt-1 text-sm text-slate-400">Running…</p>
        </li>
      )}
    </ol>
  );
}
