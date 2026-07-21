"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui";
import { Activity, CalendarCheck, FileText, ShieldCheck, Users, Workflow } from "lucide-react";

const AGENTS = [
  { icon: Workflow, name: "Coordinator", desc: "Understands the request and orchestrates the team." },
  { icon: ShieldCheck, name: "Safety & Escalation", desc: "Blocks clinical advice, escalates emergencies to humans." },
  { icon: Activity, name: "Department Routing", desc: "Maps the request to the right department administratively." },
  { icon: CalendarCheck, name: "Appointment", desc: "Checks availability & conflicts, books/reschedules/cancels." },
  { icon: FileText, name: "Document", desc: "Classifies, de-duplicates & checks for missing documents." },
  { icon: Users, name: "Follow-up", desc: "Schedules reminders and post-visit follow-up tasks." },
];

export default function Landing() {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && user) router.replace(user.role === "patient" ? "/patient" : "/staff");
  }, [ready, user, router]);

  return (
    <main className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2 text-lg font-bold text-brand-700">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white">A</div>
          AgentCare
        </div>
        <div className="flex gap-2">
          <Link href="/login"><Button variant="secondary">Sign in</Button></Link>
          <Link href="/register"><Button>Get started</Button></Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-8 pt-10">
        <div className="grid items-center gap-10 md:grid-cols-2">
          <div className="animate-fade-in">
            <span className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700">
              <ShieldCheck className="h-3.5 w-3.5" /> Administration only — medical decisions stay with clinicians
            </span>
            <h1 className="mt-4 text-4xl font-extrabold leading-tight text-slate-900 md:text-5xl">
              Agentic AI for patient <span className="text-brand-600">administration</span> & care coordination
            </h1>
            <p className="mt-4 text-lg text-slate-600">
              Submit a request in plain language — “I need a cardiology follow-up next week and want to
              attach my ECG.” A team of specialized agents plans the steps, invokes real tools, persists
              every action, and hands anything sensitive to a human.
            </p>
            <div className="mt-6 flex gap-3">
              <Link href="/register"><Button className="px-6 py-3 text-base">Create patient account</Button></Link>
              <Link href="/login"><Button variant="secondary" className="px-6 py-3 text-base">Staff sign in</Button></Link>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {AGENTS.map((a) => (
              <div key={a.name} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <a.icon className="h-6 w-6 text-brand-600" />
                <p className="mt-2 font-semibold text-slate-800">{a.name} Agent</p>
                <p className="mt-1 text-sm text-slate-500">{a.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-6 py-10 text-sm text-slate-400">
        AgentCare · not a diagnosis or treatment system · all sample data is synthetic.
      </footer>
    </main>
  );
}
