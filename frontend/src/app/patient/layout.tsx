"use client";

import { AppShell } from "@/components/AppShell";
import { CalendarCheck, FileText, LayoutDashboard, Bell } from "lucide-react";

const NAV = [
  { href: "/patient", label: "New request", icon: LayoutDashboard },
  { href: "/patient/appointments", label: "Appointments", icon: CalendarCheck },
  { href: "/patient/documents", label: "Documents", icon: FileText },
  { href: "/patient/reminders", label: "Reminders", icon: Bell },
];

export default function PatientLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell nav={NAV} allow={["patient"]} portalName="Patient portal">
      {children}
    </AppShell>
  );
}
