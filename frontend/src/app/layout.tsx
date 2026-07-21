import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "AgentCare — Patient Administration & Care Coordination",
  description:
    "Agentic AI that coordinates a patient's non-clinical journey: registration, routing, appointments, documents, reminders, and follow-up — with human oversight.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
