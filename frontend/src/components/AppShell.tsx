"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import type { Role } from "@/lib/types";
import { cn } from "@/lib/utils";
import { LogOut } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

export function AppShell({
  children,
  nav,
  allow,
  portalName,
}: {
  children: React.ReactNode;
  nav: NavItem[];
  allow: Role[];
  portalName: string;
}) {
  const { user, ready, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!ready) return;
    if (!user) router.replace("/login");
    else if (!allow.includes(user.role)) router.replace(user.role === "patient" ? "/patient" : "/staff");
  }, [ready, user, allow, router]);

  if (!ready || !user || !allow.includes(user.role)) {
    return <div className="grid min-h-screen place-items-center text-slate-400">Loading…</div>;
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white md:flex">
        <div className="flex items-center gap-2 px-5 py-5 text-lg font-bold text-brand-700">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white">A</div>
          AgentCare
        </div>
        <div className="px-4 text-xs font-medium uppercase tracking-wide text-slate-400">{portalName}</div>
        <nav className="mt-3 flex-1 space-y-1 px-3">
          {nav.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
                  active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100",
                )}
              >
                <item.icon className="h-4.5 w-4.5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-100 p-3">
          <div className="px-2 pb-2 text-sm">
            <p className="font-medium text-slate-700">{user.name}</p>
            <p className="text-xs capitalize text-slate-400">{user.role}</p>
          </div>
          <button
            onClick={() => { logout(); router.replace("/login"); }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 md:hidden">
          <span className="font-bold text-brand-700">AgentCare</span>
          <button onClick={() => { logout(); router.replace("/login"); }} className="text-sm text-slate-500">Sign out</button>
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
