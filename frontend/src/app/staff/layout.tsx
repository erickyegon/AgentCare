"use client";

import { AppShell } from "@/components/AppShell";
import { AlertTriangle, ClipboardList, LayoutDashboard, ScrollText, Stethoscope, Users } from "lucide-react";

const NAV = [
  { href: "/staff", label: "Overview", icon: LayoutDashboard },
  { href: "/staff/escalations", label: "Escalations", icon: AlertTriangle },
  { href: "/staff/workflows", label: "Workflows", icon: ClipboardList },
  { href: "/staff/patients", label: "Patients", icon: Users },
  { href: "/staff/catalog", label: "Departments", icon: Stethoscope },
  { href: "/staff/audit", label: "Audit log", icon: ScrollText },
];

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell nav={NAV} allow={["staff", "admin"]} portalName="Staff console">
      {children}
    </AppShell>
  );
}
