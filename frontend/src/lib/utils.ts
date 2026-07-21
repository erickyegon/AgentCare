import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function titleCase(s: string): string {
  return s
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export const AGENT_META: Record<string, { label: string; color: string; icon: string }> = {
  coordinator_agent: { label: "Coordinator", color: "bg-brand-100 text-brand-800", icon: "🧭" },
  safety_agent: { label: "Safety & Escalation", color: "bg-red-100 text-red-800", icon: "🛡️" },
  routing_agent: { label: "Department Routing", color: "bg-amber-100 text-amber-800", icon: "🔀" },
  appointment_agent: { label: "Appointment", color: "bg-teal-100 text-teal-700", icon: "📅" },
  document_agent: { label: "Document", color: "bg-violet-100 text-violet-800", icon: "📄" },
  followup_agent: { label: "Follow-up", color: "bg-emerald-100 text-emerald-800", icon: "🔔" },
};

export const STATUS_COLORS: Record<string, string> = {
  completed: "bg-emerald-100 text-emerald-800",
  confirmed: "bg-emerald-100 text-emerald-800",
  running: "bg-brand-100 text-brand-800",
  pending: "bg-slate-100 text-slate-700",
  escalated: "bg-amber-100 text-amber-800",
  awaiting_approval: "bg-amber-100 text-amber-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-slate-200 text-slate-600",
  rescheduled: "bg-teal-100 text-teal-700",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
  halted: "bg-red-100 text-red-800",
};
