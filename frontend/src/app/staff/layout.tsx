"use client";

import { AppShell } from "@/components/AppShell";
import { AlertTriangle, BarChart3, ClipboardList, HelpCircle, LayoutDashboard, ScrollText, Stethoscope, Users } from "lucide-react";

const NAV = [
  { href: "/staff", label: "Overview", icon: LayoutDashboard },
  { href: "/staff/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/staff/escalations", label: "Escalations", icon: AlertTriangle },
  { href: "/staff/workflows", label: "Workflows", icon: ClipboardList },
  { href: "/staff/patients", label: "Patients", icon: Users },
  { href: "/staff/catalog", label: "Departments", icon: Stethoscope },
  { href: "/staff/audit", label: "Audit log", icon: ScrollText },
  { href: "/help", label: "Help", icon: HelpCircle },
];

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell nav={NAV} allow={["staff", "admin"]} portalName="Staff console">
      {children}
    </AppShell>
  );
}
