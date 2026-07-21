"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AuthUser } from "@/lib/types";
import { Button, Card, Input } from "@/components/ui";

const DEMO = [
  { label: "Patient", email: "patient@agentcare.io" },
  { label: "Staff", email: "staff@agentcare.io" },
  { label: "Admin", email: "admin@agentcare.io" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await api.post<AuthUser>("/auth/login", { email, password }, false);
      login(user);
      router.replace(user.role === "patient" ? "/patient" : "/staff");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4">
      <Card className="w-full max-w-md p-8">
        <Link href="/" className="mb-6 flex items-center gap-2 text-lg font-bold text-brand-700">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white">A</div>
          AgentCare
        </Link>
        <h1 className="text-xl font-semibold text-slate-800">Sign in</h1>
        <p className="mt-1 text-sm text-slate-500">Access your patient portal or staff console.</p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <Input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </div>
          {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <Button type="submit" loading={loading} className="w-full">Sign in</Button>
        </form>

        <div className="mt-6 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
          <p className="font-medium text-slate-600">Demo accounts (password: <code>AgentCare!2026</code>)</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {DEMO.map((d) => (
              <button
                key={d.email}
                type="button"
                onClick={() => { setEmail(d.email); setPassword("AgentCare!2026"); }}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 hover:border-brand-400"
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <p className="mt-6 text-center text-sm text-slate-500">
          New patient? <Link href="/register" className="font-medium text-brand-600">Create an account</Link>
        </p>
      </Card>
    </main>
  );
}
