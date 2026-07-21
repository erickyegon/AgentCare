"use client";

/**
 * A small, principled chart kit (hand-built, no chart lib).
 * Follows the data-viz method: form chosen by the data's job, validated palette,
 * thin marks with 4px rounded data-ends + 2px gaps, direct labels, a hover layer,
 * a legend for multi-series, and a table fallback for accessibility.
 */

import { useState } from "react";
import { cn, titleCase } from "@/lib/utils";
import { Table2 } from "lucide-react";

export interface Datum {
  label: string;
  value: number;
  /** status role for state distributions; omitted → single sequential-blue series */
  role?: "good" | "warning" | "critical" | "neutral" | "info";
}

const ROLE_VAR: Record<string, string> = {
  good: "var(--status-good)",
  warning: "var(--status-warning)",
  critical: "var(--status-critical)",
  neutral: "var(--status-neutral)",
  info: "var(--status-info)",
};

/** Map a workflow/appointment status or escalation category to a status role. */
export function statusRole(key: string): Datum["role"] {
  const k = key.toLowerCase();
  if (["completed", "confirmed", "approved", "sent", "scheduled"].includes(k)) return "good";
  if (["escalated", "awaiting_approval", "pending", "rescheduled"].includes(k)) return "warning";
  if (["failed", "rejected", "cancelled", "emergency", "self_harm"].includes(k)) return "critical";
  if (["running"].includes(k)) return "info";
  return "neutral";
}

/* ---------------------------------------------------------------- Stat tile */

export function StatTile({
  icon: Icon,
  label,
  value,
  sub,
  accent = "var(--series-1)",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number | string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="viz rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="flex items-center justify-between">
        <span className="grid h-9 w-9 place-items-center rounded-xl text-brand-700" style={{ background: "var(--series-1-soft)" }}>
          <Icon className="h-5 w-5" />
        </span>
        <span className="h-1.5 w-1.5 rounded-full" style={{ background: accent }} />
      </div>
      <p className="mt-3 text-3xl font-bold tracking-tight text-slate-900">{value}</p>
      <p className="text-sm font-medium text-slate-600">{label}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

/* --------------------------------------------------------- Ranked H-bars */

export function RankedBars({ data, unit = "" }: { data: Datum[]; unit?: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const sorted = [...data].sort((a, b) => b.value - a.value);
  const max = Math.max(1, ...sorted.map((d) => d.value));
  if (sorted.length === 0 || sorted.every((d) => d.value === 0))
    return <p className="py-6 text-center text-sm text-slate-400">No data yet.</p>;

  return (
    <div className="viz space-y-2.5">
      {sorted.map((d, i) => {
        const pct = (d.value / max) * 100;
        const fill = d.role ? ROLE_VAR[d.role] : "var(--series-1)";
        return (
          <div
            key={d.label}
            className="grid grid-cols-[minmax(84px,120px)_1fr_auto] items-center gap-3"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          >
            <span className="truncate text-sm capitalize text-slate-600" title={titleCase(d.label)}>
              {titleCase(d.label)}
            </span>
            <div className="h-2.5 rounded-full" style={{ background: "var(--viz-grid)" }}>
              <div
                className="h-2.5 rounded-full transition-all duration-500"
                style={{
                  width: `${Math.max(pct, 2)}%`,
                  background: fill,
                  opacity: hover === null || hover === i ? 1 : 0.45,
                }}
              />
            </div>
            <span className="w-10 text-right text-sm font-semibold tabular-nums text-slate-800">
              {d.value}
              {unit}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------ Donut chart */

export function DonutChart({ data, centerLabel }: { data: Datum[]; centerLabel?: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <p className="py-6 text-center text-sm text-slate-400">No data yet.</p>;

  const r = 56;
  const stroke = 18;
  const C = 2 * Math.PI * r;
  const gap = 2; // 2px surface gap between segments
  let offset = 0;
  const segments = data.filter((d) => d.value > 0);

  return (
    <div className="viz flex flex-col items-center gap-5 sm:flex-row sm:items-center sm:gap-6">
      <div className="relative shrink-0">
        <svg width="150" height="150" viewBox="0 0 150 150" role="img" aria-label="Distribution donut chart">
          <g transform="rotate(-90 75 75)">
            {segments.map((d, i) => {
              const frac = d.value / total;
              const len = Math.max(frac * C - gap, 0.5);
              const dash = `${len} ${C - len}`;
              const el = (
                <circle
                  key={d.label}
                  cx="75"
                  cy="75"
                  r={r}
                  fill="none"
                  stroke={d.role ? ROLE_VAR[d.role] : "var(--series-1)"}
                  strokeWidth={hover === i ? stroke + 4 : stroke}
                  strokeDasharray={dash}
                  strokeDashoffset={-offset}
                  style={{ transition: "stroke-width .2s", opacity: hover === null || hover === i ? 1 : 0.5 }}
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                />
              );
              offset += frac * C;
              return el;
            })}
          </g>
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold tabular-nums text-slate-900">
            {hover !== null ? segments[hover].value : total}
          </span>
          <span className="max-w-[80px] text-center text-[11px] capitalize leading-tight text-slate-400">
            {hover !== null ? titleCase(segments[hover].label) : centerLabel || "total"}
          </span>
        </div>
      </div>

      {/* Legend — identity via swatch + label (never colour alone) */}
      <ul className="flex-1 space-y-1.5">
        {segments.map((d, i) => (
          <li
            key={d.label}
            className="flex items-center gap-2 rounded-md px-1.5 py-1 text-sm"
            style={{ background: hover === i ? "var(--viz-grid)" : "transparent" }}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          >
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: d.role ? ROLE_VAR[d.role] : "var(--series-1)" }} />
            <span className="flex-1 capitalize text-slate-600">{titleCase(d.label)}</span>
            <span className="font-semibold tabular-nums text-slate-800">{d.value}</span>
            <span className="w-10 text-right text-xs tabular-nums text-slate-400">
              {Math.round((d.value / total) * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* --------------------------------------------------- Card + table fallback */

export function ChartCard({
  title,
  subtitle,
  data,
  children,
}: {
  title: string;
  subtitle?: string;
  data: Datum[];
  children: React.ReactNode;
}) {
  const [asTable, setAsTable] = useState(false);
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-start justify-between border-b border-slate-100 px-5 py-3.5">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
          {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
        </div>
        <button
          onClick={() => setAsTable((v) => !v)}
          className={cn(
            "flex items-center gap-1 rounded-md px-2 py-1 text-xs transition",
            asTable ? "bg-brand-50 text-brand-700" : "text-slate-400 hover:bg-slate-100",
          )}
          aria-pressed={asTable}
          title="Toggle table view"
        >
          <Table2 className="h-3.5 w-3.5" /> Table
        </button>
      </div>
      <div className="p-5">
        {asTable ? (
          <table className="w-full text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="pb-2 text-left font-medium">Category</th>
                <th className="pb-2 text-right font-medium">Count</th>
                <th className="pb-2 text-right font-medium">Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {[...data].sort((a, b) => b.value - a.value).map((d) => (
                <tr key={d.label}>
                  <td className="py-1.5 capitalize text-slate-700">{titleCase(d.label)}</td>
                  <td className="py-1.5 text-right tabular-nums text-slate-800">{d.value}</td>
                  <td className="py-1.5 text-right tabular-nums text-slate-400">
                    {total ? Math.round((d.value / total) * 100) : 0}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------- Skeletons */

export function ChartSkeleton() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="skeleton mb-4 h-4 w-1/3" />
      <div className="space-y-3">
        {[80, 60, 45, 30].map((w, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="skeleton h-3 w-20" />
            <div className="skeleton h-2.5 flex-1" style={{ maxWidth: `${w}%` }} />
          </div>
        ))}
      </div>
    </div>
  );
}
