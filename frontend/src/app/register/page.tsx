"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AuthUser } from "@/lib/types";
import { Button, Card, Input } from "@/components/ui";

export default function RegisterPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ name: "", email: "", password: "", phone: "", preferred_language: "English" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await api.post<AuthUser>("/auth/register", form, false);
      login(user);
      router.replace("/patient");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4 py-8">
      <Card className="w-full max-w-md p-8">
        <Link href="/" className="mb-6 flex items-center gap-2 text-lg font-bold text-brand-700">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white">A</div>
          AgentCare
        </Link>
        <h1 className="text-xl font-semibold text-slate-800">Create patient account</h1>
        <p className="mt-1 text-sm text-slate-500">Self-registration creates a patient profile.</p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <Field label="Full name"><Input required value={form.name} onChange={(e) => set("name", e.target.value)} /></Field>
          <Field label="Email"><Input type="email" required value={form.email} onChange={(e) => set("email", e.target.value)} /></Field>
          <Field label="Password (min 8 chars)"><Input type="password" required minLength={8} value={form.password} onChange={(e) => set("password", e.target.value)} /></Field>
          <Field label="Phone (optional)"><Input value={form.phone} onChange={(e) => set("phone", e.target.value)} /></Field>
          {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <Button type="submit" loading={loading} className="w-full">Create account</Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account? <Link href="/login" className="font-medium text-brand-600">Sign in</Link>
        </p>
      </Card>
    </main>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      {children}
    </div>
  );
}
