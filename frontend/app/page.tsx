import IncidentDashboard from "@/components/incident-dashboard";
import type { IncidentSummary, IncidentTemplate, PlatformMetrics } from "@/lib/incident-dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export default async function Page() {
  const [initialIncidents, initialTemplates, initialMetrics] = await Promise.all([
    fetchJson<IncidentSummary[]>("/api/incidents").catch(() => []),
    fetchJson<IncidentTemplate[]>("/api/incidents/templates").catch(() => []),
    fetchJson<PlatformMetrics>("/api/incidents/metrics/summary").catch(() => null),
  ]);

  return (
    <IncidentDashboard
      initialIncidents={initialIncidents}
      initialTemplates={initialTemplates}
      initialMetrics={initialMetrics}
    />
  );
}
