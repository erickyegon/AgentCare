"use client";

import Link from "next/link";
import { useState } from "react";
import { Card } from "@/components/ui";
import { cn } from "@/lib/utils";
import { ArrowLeft, ShieldCheck } from "lucide-react";

const TABS = ["Patients", "Staff", "Safety"] as const;
type Tab = (typeof TABS)[number];

export default function HelpPage() {
  const [tab, setTab] = useState<Tab>("Patients");

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <Link href="/" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
        <ArrowLeft className="h-4 w-4" /> Home
      </Link>
      <h1 className="mt-3 text-2xl font-bold text-slate-900">AgentCare user guide</h1>
      <p className="mt-1 text-slate-500">How to use the patient portal and staff console.</p>

      <div className="mt-5 flex gap-1 rounded-lg border border-slate-200 bg-white p-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn("flex-1 rounded-md px-3 py-1.5 text-sm font-medium",
              tab === t ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100")}
          >
            {t}
          </button>
        ))}
      </div>

      <Card className="mt-4 p-6">
        {tab === "Patients" && (
          <Guide
            heading="For patients"
            steps={[
              ["Create an account or sign in", "Use the demo Patient button on the login page, or register. Your patient profile (with an MRN) is created automatically."],
              ["Upload documents (optional)", "On New request or Documents, upload files like an ECG, blood report, or referral. Each is classified and checked for duplicates by checksum."],
              ["Submit a request in plain language", "e.g. “I need a cardiology follow-up next week and want to attach my old ECG.” Optionally tick documents to attach."],
              ["Watch the live agent trace", "Six agents coordinate: understand → safety → routing → appointment → documents → follow-up. You’ll see each step as it happens."],
              ["Review the result", "A confirmation is built from real records: your appointment code, any missing required documents, and scheduled reminders."],
              ["Manage everything", "Use Appointments, Documents, and Reminders. You can cancel an appointment; late cancellations are sent to staff for approval."],
              ["Download a report", "Open any request and click Report to download a printable summary of the whole coordination."],
            ]}
          />
        )}
        {tab === "Staff" && (
          <Guide
            heading="For staff & administrators"
            steps={[
              ["Sign in as staff/admin", "Use the demo Staff/Admin buttons or your account. Staff-only routes are enforced in the backend."],
              ["Overview & Analytics", "See totals and live charts (workflows, appointments, escalations, reminders, department load) computed from the database."],
              ["Review escalations", "Emergencies, clinical questions, uncertain routing, and late cancellations arrive here. Approve or reject with a note — the decision is persisted with your identity."],
              ["Approve gated actions", "Approving a late-cancellation actually performs the cancellation; rejecting restores the appointment."],
              ["Inspect workflows", "Open any run to see the full agent trace, escalations, and its audit trail. Download a report for records."],
              ["Manage the catalog", "Add departments (the routing agent can only route to departments that exist), doctors, and slots."],
              ["Audit log", "Every agent and human action is recorded immutably and searchable per run."],
            ]}
          />
        )}
        {tab === "Safety" && (
          <div>
            <div className="mb-3 flex items-center gap-2 text-teal-700">
              <ShieldCheck className="h-5 w-5" />
              <h2 className="font-semibold">Safety boundary</h2>
            </div>
            <p className="text-sm text-slate-600">
              AgentCare handles <b>administration and coordination only</b>. It never diagnoses,
              interprets results, prescribes, changes dosages, or claims to replace a clinician.
            </p>
            <ul className="mt-4 space-y-3 text-sm text-slate-600">
              <li><b>Emergencies</b> (e.g. chest pain, difficulty breathing) — the Safety agent halts the automated workflow, advises contacting emergency services, and raises a critical escalation for staff.</li>
              <li><b>Clinical questions</b> (diagnosis, medication, dosage, result interpretation) — refused and escalated to a clinician; any administrative parts (like booking) still proceed.</li>
              <li><b>Sensitive actions</b> — e.g. late cancellations require staff approval before they take effect.</li>
              <li><b>Privacy</b> — patients can only see and act on their own records; all sample data is synthetic; secrets stay in a local, gitignored file.</li>
            </ul>
            <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              If you are experiencing a medical emergency, contact your local emergency number or go to
              the nearest emergency department immediately.
            </p>
          </div>
        )}
      </Card>
    </main>
  );
}

function Guide({ heading, steps }: { heading: string; steps: [string, string][] }) {
  return (
    <div>
      <h2 className="mb-4 font-semibold text-slate-800">{heading}</h2>
      <ol className="space-y-4">
        {steps.map(([title, body], i) => (
          <li key={i} className="flex gap-3">
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">{i + 1}</span>
            <div>
              <p className="font-medium text-slate-800">{title}</p>
              <p className="text-sm text-slate-500">{body}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
