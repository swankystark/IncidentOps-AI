import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IncidentOps AI | Autonomous Incident Investigation & Remediation",
  description: "Autonomous Tier-3 Incident response and remediation agent that investigates logs, commits, pipelines, and patches production bugs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
