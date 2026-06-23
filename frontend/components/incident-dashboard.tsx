"use client";

import { useEffect, useMemo, useState } from "react";
import {
  buildTimeline,
  diffSummary,
  formatTimestamp,
  IncidentDetail,
  IncidentSummary,
  IncidentTemplate,
  parseRcaReport,
  phaseTone,
  PlatformMetrics,
  RepositoryValidation,
  severityTone,
  statusTone,
} from "@/lib/incident-dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const DEMO_PRESET = {
  targetRepo: "swankystark20-group/incidentops-demo-app",
  targetBranch: "main",
  targetAppPath: "invoice-app",
  applicationLogPath: "invoice-app/application.log",
};

const evidenceTabs = [
  ["logs", "Runtime Logs"],
  ["gitlab", "GitLab Evidence"],
  ["cicd", "CI/CD Evidence"],
] as const;

type IncidentDashboardProps = {
  initialIncidents: IncidentSummary[];
  initialTemplates: IncidentTemplate[];
  initialMetrics: PlatformMetrics | null;
};

async function apiFetch(path: string, init?: RequestInit) {
  if (!API_BASE_URL) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured in frontend/.env.local");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {}
    throw new Error(message);
  }
  return response;
}

function cx(...parts: Array<string | false | undefined>) {
  return parts.filter(Boolean).join(" ");
}

function badge(status?: string) {
  return cx(
    "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium tracking-[0.08em] uppercase",
    statusTone(status)
  );
}

function panelClass(extra = "") {
  return cx("panel rounded-[28px] p-5 md:p-6", extra);
}

function metricCard(label: string, value: string | number, meta: string) {
  return (
    <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(10,16,27,0.82)] p-4">
      <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{value}</div>
      <div className="mt-1 text-sm text-[var(--text-secondary)]">{meta}</div>
    </div>
  );
}

function sectionTitle(title: string, description: string) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <div className="text-[11px] uppercase tracking-[0.2em] text-[var(--text-tertiary)]">IncidentOps AI</div>
        <h2 className="mt-2 text-xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">{title}</h2>
      </div>
      <p className="max-w-xl text-sm leading-6 text-[var(--text-secondary)]">{description}</p>
    </div>
  );
}

function keyValue(label: string, value: string | number | undefined) {
  return (
    <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(10,16,27,0.78)] p-4">
      <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">{label}</div>
      <div className="mt-2 break-words text-sm text-[var(--text-primary)]">{value || "—"}</div>
    </div>
  );
}

function severityLabel(level?: string) {
  const value = (level || "INFO").toUpperCase();
  if (value.includes("ERROR")) return "Error";
  if (value.includes("WARNING")) return "Warning";
  return "Info";
}

export default function IncidentDashboard({
  initialIncidents,
  initialTemplates,
  initialMetrics,
}: IncidentDashboardProps) {
  const [incidents, setIncidents] = useState<IncidentSummary[]>(initialIncidents);
  const templates = initialTemplates;
  const metrics = initialMetrics;
  const [selectedIncidentId, setSelectedIncidentId] = useState<number | null>(
    initialIncidents[0]?.id ?? null
  );
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<(typeof evidenceTabs)[number][0]>("logs");
  const [selectedTemplateId, setSelectedTemplateId] = useState("INC-101");
  const [ticketId, setTicketId] = useState("INC-101");
  const [repoForm, setRepoForm] = useState(DEMO_PRESET);
  const [repoValidation, setRepoValidation] = useState<RepositoryValidation | null>(null);
  const [busy, setBusy] = useState<"refresh" | "trigger" | "validate" | "resume" | null>(null);
  const [error, setError] = useState("");

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? templates[0],
    [selectedTemplateId, templates]
  );

  const selectedIncident = useMemo(
    () => incidents.find((incident) => incident.id === selectedIncidentId) ?? null,
    [incidents, selectedIncidentId]
  );

  const timeline = useMemo(() => buildTimeline(detail), [detail]);
  const rca = useMemo(() => parseRcaReport(detail?.rca_report), [detail?.rca_report]);
  const diffStats = useMemo(() => diffSummary(detail?.patch_diff), [detail?.patch_diff]);
  const validationLogs = useMemo(
    () => detail?.logs.filter((log) => log.agent_name === "Validation Service") ?? [],
    [detail]
  );
  const cicdLogs = useMemo(
    () => detail?.logs.filter((log) => log.agent_name === "CI/CD Service") ?? [],
    [detail]
  );

  async function loadIncidents() {
    const response = await apiFetch("/api/incidents");
    const data = await response.json();
    setIncidents(data);
    if (!selectedIncidentId && data[0]) {
      setSelectedIncidentId(data[0].id);
      await loadIncident(data[0].id);
    }
  }

  async function loadIncident(id: number) {
    try {
      const response = await apiFetch(`/api/incidents/${id}`);
      setDetail(await response.json());
      setError("");
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleValidateRepository() {
    setBusy("validate");
    setError("");
    try {
      const response = await apiFetch("/api/config/repository/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_repo: repoForm.targetRepo,
          target_branch: repoForm.targetBranch,
        }),
      });
      setRepoValidation(await response.json());
    } catch (err) {
      setRepoValidation(null);
      setError(String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleTriggerIncident() {
    if (!selectedTemplate) return;
    setBusy("trigger");
    setError("");
    try {
      const response = await apiFetch("/api/incidents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticket_id: ticketId || selectedTemplate.id,
          scenario_id: selectedTemplate.id,
          title: selectedTemplate.title,
          description: selectedTemplate.description,
          target_repo: repoForm.targetRepo,
          target_branch: repoForm.targetBranch,
          target_app_path: repoForm.targetAppPath,
          application_log_path: repoForm.applicationLogPath,
        }),
      });
      const created = await response.json();
      await loadIncidents();
      setSelectedIncidentId(created.id);
      await loadIncident(created.id);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleSelectIncident(id: number) {
    setSelectedIncidentId(id);
    await loadIncident(id);
  }

  useEffect(() => {
    if (selectedIncidentId) {
      void loadIncident(selectedIncidentId);
    }
  }, [selectedIncidentId]);

  async function handleResume() {
    if (!selectedIncident) return;
    setBusy("resume");
    setError("");
    try {
      await apiFetch(`/api/incidents/${selectedIncident.id}/resume`, { method: "POST" });
      await loadIncident(selectedIncident.id);
      await loadIncidents();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(null);
    }
  }

  const currentPhase = timeline.find((phase) => phase.status === "running") ?? timeline.find((phase) => phase.status === "warning") ?? timeline.find((phase) => phase.status === "complete");

  return (
    <main className="min-h-screen">
      <div className="grid-mesh absolute inset-0 -z-10 opacity-40" />
      <div className="mx-auto flex max-w-[1440px] flex-col gap-6 px-4 py-4 md:px-6 md:py-6">
        <header className={panelClass("overflow-hidden")}>
          <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
            <div className="max-w-3xl">
              <div className="text-[11px] uppercase tracking-[0.22em] text-[var(--text-tertiary)]">IncidentOps AI</div>
              <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-[var(--text-primary)] md:text-5xl">
                Incident Dashboard
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--text-secondary)]">
                Observe the incident lifecycle from planner to merge request. Every view in this workspace maps to the
                backend architecture: timeline, evidence, root cause, patch diff, validation, and remediation.
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <span className={badge(detail?.status)}>{detail?.status || "No incident selected"}</span>
                <span className={badge(detail?.validation_strategy || "Validation")}>
                  {detail?.validation_strategy || "validation strategy"}
                </span>
                <span className={badge(repoValidation?.ok ? "RESOLVED" : repoValidation ? "WAITING_FOR_RETRY" : "INVESTIGATING")}>
                  {repoValidation?.ok ? "repository validated" : repoValidation ? "validation blocked" : "repository status"}
                </span>
              </div>
            </div>

            <div className="grid w-full gap-3 sm:grid-cols-2 xl:w-[520px]">
              {metricCard("Investigation time", `${metrics?.average_investigation_time_seconds?.toFixed(1) ?? "—"}s`, "Mean end-to-end duration")}
              {metricCard("Confidence", `${metrics?.average_root_cause_confidence?.toFixed(1) ?? "—"}%`, "Root cause certainty")}
              {metricCard("Validation", `${Math.round((metrics?.validation_success_rate ?? 0) * 100)}%`, "Pass rate")}
              {metricCard("MRs", metrics?.merge_requests_created ?? "—", "Remediations created")}
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-2 border-t border-[color:var(--border-subtle)] pt-5">
            {timeline.map((phase) => (
              <span
                key={phase.key}
                className={cx(
                  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium",
                  phaseTone(phase.status)
                )}
              >
                {phase.label}
              </span>
            ))}
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
          <aside className={panelClass("sticky top-4 h-fit")}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Incident rail</div>
                <h2 className="mt-2 text-lg font-semibold text-[var(--text-primary)]">Incident queue</h2>
              </div>
              <button
                type="button"
                onClick={() =>
                  void loadIncidents().catch((err) => {
                    setError(String(err));
                  })
                }
                className="rounded-full border border-[color:var(--border-default)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition hover:border-[color:var(--accent-primary)] hover:text-[var(--text-primary)]"
              >
                Refresh
              </button>
            </div>

            <div className="mt-5 space-y-3">
              {incidents.map((incident) => {
                const active = incident.id === selectedIncidentId;
                return (
                  <button
                    key={incident.id}
                    type="button"
                    onClick={() => void handleSelectIncident(incident.id)}
                    className={cx(
                      "w-full rounded-2xl border p-4 text-left transition",
                      active
                        ? "border-[color:var(--accent-primary)] bg-[rgba(93,214,255,0.08)]"
                        : "border-[color:var(--border-subtle)] bg-[rgba(10,16,27,0.72)] hover:border-[color:var(--border-default)]"
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold text-[var(--text-primary)]">{incident.ticket_id}</div>
                        <div className="mt-1 text-sm text-[var(--text-secondary)]">{incident.title}</div>
                      </div>
                      <span className={cx("rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.16em]", statusTone(incident.status))}>
                        {incident.status}
                      </span>
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] text-[var(--text-tertiary)]">
                      <span>{incident.target_repo || "repo unset"}</span>
                      <span className="text-right">{incident.target_branch || "main"}</span>
                      <span>{incident.confidence_score ? `${incident.confidence_score}% confidence` : "pending confidence"}</span>
                      <span className="text-right">{formatTimestamp(incident.updated_at)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>

          <div className="space-y-6">
            <section className={panelClass()}>
              {sectionTitle(
                "Incident Dashboard",
                "Use this panel to select the incident template, validate the repository, and trigger a run. It is the product control surface for the backend architecture."
              )}

              {error ? (
                <div className="mt-5 rounded-2xl border border-[color:var(--status-error)]/30 bg-[rgba(251,113,133,0.1)] p-4 text-sm text-[color:var(--status-error)]">
                  {error}
                </div>
              ) : null}

              <div className="mt-6 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Incident template</span>
                    <select
                      value={selectedTemplateId}
                      onChange={(event) => {
                        setSelectedTemplateId(event.target.value);
                        setTicketId(event.target.value);
                      }}
                      className="w-full rounded-2xl border border-[color:var(--border-default)] bg-[rgba(10,16,27,0.82)] px-4 py-3 text-sm text-[var(--text-primary)] outline-none transition focus:border-[color:var(--accent-primary)]"
                    >
                      {templates.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.id} · {template.module}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Ticket ID</span>
                    <input
                      value={ticketId}
                      onChange={(event) => setTicketId(event.target.value)}
                      className="w-full rounded-2xl border border-[color:var(--border-default)] bg-[rgba(10,16,27,0.82)] px-4 py-3 text-sm text-[var(--text-primary)] outline-none transition focus:border-[color:var(--accent-primary)]"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Target repo</span>
                    <input
                      value={repoForm.targetRepo}
                      onChange={(event) => setRepoForm((current) => ({ ...current, targetRepo: event.target.value }))}
                      className="w-full rounded-2xl border border-[color:var(--border-default)] bg-[rgba(10,16,27,0.82)] px-4 py-3 text-sm text-[var(--text-primary)] outline-none transition focus:border-[color:var(--accent-primary)]"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Branch</span>
                    <input
                      value={repoForm.targetBranch}
                      onChange={(event) => setRepoForm((current) => ({ ...current, targetBranch: event.target.value }))}
                      className="w-full rounded-2xl border border-[color:var(--border-default)] bg-[rgba(10,16,27,0.82)] px-4 py-3 text-sm text-[var(--text-primary)] outline-none transition focus:border-[color:var(--accent-primary)]"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">App path</span>
                    <input
                      value={repoForm.targetAppPath}
                      onChange={(event) => setRepoForm((current) => ({ ...current, targetAppPath: event.target.value }))}
                      className="w-full rounded-2xl border border-[color:var(--border-default)] bg-[rgba(10,16,27,0.82)] px-4 py-3 text-sm text-[var(--text-primary)] outline-none transition focus:border-[color:var(--accent-primary)]"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Log path</span>
                    <input
                      value={repoForm.applicationLogPath}
                      onChange={(event) =>
                        setRepoForm((current) => ({ ...current, applicationLogPath: event.target.value }))
                      }
                      className="w-full rounded-2xl border border-[color:var(--border-default)] bg-[rgba(10,16,27,0.82)] px-4 py-3 text-sm text-[var(--text-primary)] outline-none transition focus:border-[color:var(--accent-primary)]"
                    />
                  </label>
                </div>

                <div className="flex flex-col justify-between rounded-[24px] border border-[color:var(--border-subtle)] bg-[rgba(10,16,27,0.8)] p-5">
                  <div className="space-y-4">
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Workflow overview</div>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                        {currentPhase
                          ? `${currentPhase.label} is the active stage. The current flow is planner, logs, GitLab, CI/CD, fusion, context, patch, validation, and MR.`
                          : "Choose or trigger an incident to reveal the lifecycle in motion."}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      {keyValue("Selected incident", selectedIncident?.ticket_id)}
                      {keyValue("Root cause confidence", selectedIncident?.confidence_score ? `${selectedIncident.confidence_score}%` : "—")}
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      {keyValue("Repository", repoValidation?.project_name || repoForm.targetRepo)}
                      {keyValue("Validation", repoValidation?.ok ? "PASS" : repoValidation ? "CHECK" : "—")}
                    </div>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => setRepoForm(DEMO_PRESET)}
                      className="rounded-full border border-[color:var(--border-default)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition hover:border-[color:var(--accent-primary)] hover:text-[var(--text-primary)]"
                    >
                      Apply Demo Preset
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleValidateRepository()}
                      disabled={busy === "validate"}
                      className="rounded-full border border-[color:var(--accent-primary)] bg-[rgba(93,214,255,0.10)] px-4 py-2 text-sm font-medium text-[color:var(--accent-primary)] transition hover:bg-[rgba(93,214,255,0.16)] disabled:opacity-60"
                    >
                      {busy === "validate" ? "Validating..." : "Validate Repository"}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleTriggerIncident()}
                      disabled={busy === "trigger"}
                      className="rounded-full bg-[color:var(--text-primary)] px-4 py-2 text-sm font-semibold text-[color:var(--surface-base)] transition hover:bg-[rgba(244,247,251,0.92)] disabled:opacity-60"
                    >
                      {busy === "trigger" ? "Triggering..." : "Trigger Incident"}
                    </button>
                    {selectedIncident?.status === "WAITING_FOR_RETRY" ? (
                      <button
                        type="button"
                        onClick={() => void handleResume()}
                        disabled={busy === "resume"}
                        className="rounded-full border border-[color:var(--status-warning)]/40 px-4 py-2 text-sm font-medium text-[color:var(--status-warning)] transition hover:bg-[rgba(251,191,36,0.10)] disabled:opacity-60"
                      >
                        {busy === "resume" ? "Resuming..." : "Resume"}
                      </button>
                    ) : null}
                  </div>

                  {repoValidation ? (
                    <div className="mt-5 rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.55)] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-medium text-[var(--text-primary)]">{repoValidation.message}</div>
                        <span className={badge(repoValidation.ok ? "RESOLVED" : "WAITING_FOR_RETRY")}>
                          {repoValidation.ok ? "PASS" : "FAIL"}
                        </span>
                      </div>
                      <div className="mt-3 grid gap-2 text-sm text-[var(--text-secondary)] sm:grid-cols-2">
                        {keyValue("Project", repoValidation.project_name)}
                        {keyValue("Web URL", repoValidation.web_url)}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
              <article className={panelClass()}>
                {sectionTitle("Incident Timeline View", "A chronological readout of the backend workflow from planner through merge request.") }
                <ol className="mt-6 space-y-4">
                  {timeline.map((phase, index) => (
                    <li key={phase.key} className="flex gap-4">
                      <div className="flex flex-col items-center">
                        <span className={cx("status-dot mt-1 h-3 w-3 rounded-full border", phaseTone(phase.status))} />
                        {index !== timeline.length - 1 ? <span className="mt-2 h-full w-px bg-[color:var(--border-subtle)]" /> : null}
                      </div>
                      <div className="flex-1 rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(10,16,27,0.76)] p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-[var(--text-primary)]">{phase.label}</div>
                            <div className="mt-1 text-sm text-[var(--text-secondary)]">{phase.summary}</div>
                          </div>
                          <div className="text-right">
                            <span className={cx("rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.18em]", phaseTone(phase.status))}>
                              {phase.status}
                            </span>
                            <div className="mt-2 text-[11px] text-[var(--text-tertiary)]">{formatTimestamp(phase.timestamp)}</div>
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              </article>

              <article className={panelClass()}>
                {sectionTitle("Evidence Viewer", "Inspect the three evidence streams that feed fusion: logs, GitLab, and CI/CD.") }
                <div className="mt-5 flex flex-wrap gap-2">
                  {evidenceTabs.map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setSelectedEvidence(key)}
                      className={cx(
                        "rounded-full border px-3 py-1.5 text-xs font-medium transition",
                        selectedEvidence === key
                          ? "border-[color:var(--accent-primary)] bg-[rgba(93,214,255,0.1)] text-[color:var(--accent-primary)]"
                          : "border-[color:var(--border-default)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className="mt-5 space-y-3">
                  {selectedEvidence === "logs" ? (
                    detail?.logs?.length ? (
                      detail.logs.slice(-8).map((log) => (
                        <div key={log.id} className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.65)] p-4">
                          <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.16em]">
                            <span className="text-[var(--text-secondary)]">{log.agent_name}</span>
                            <span className={cx("font-medium", severityTone(log.level))}>{severityLabel(log.level)}</span>
                          </div>
                          <p className="mt-3 text-sm leading-6 text-[var(--text-primary)]">{log.message}</p>
                          <div className="mt-3 text-[11px] text-[var(--text-tertiary)]">{formatTimestamp(log.timestamp)}</div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.65)] p-5 text-sm text-[var(--text-secondary)]">
                        No incident selected yet. Trigger an incident or pick one from the left rail.
                      </div>
                    )
                  ) : null}

                  {selectedEvidence === "gitlab" ? (
                    <div className="grid gap-3">
                      {keyValue("Repository", detail?.target_repo)}
                      {keyValue("Branch", detail?.target_branch)}
                      {keyValue("Target app path", detail?.target_app_path)}
                      {keyValue("Selected commit", detail?.selected_pipeline_sha)}
                      {keyValue("Pipeline source", detail?.selected_pipeline_source)}
                    </div>
                  ) : null}

                  {selectedEvidence === "cicd" ? (
                    <div className="grid gap-3">
                      {keyValue("Pipeline status", detail?.selected_pipeline_status)}
                      {keyValue("Pipeline URL", detail?.selected_pipeline_web_url)}
                      {keyValue("Validation strategy", detail?.validation_strategy)}
                      {keyValue("Validation logs", validationLogs.at(-1)?.message || "Awaiting validation output")}
                    </div>
                  ) : null}
                </div>
              </article>

              <article className={panelClass()}>
                {sectionTitle("Root Cause Report", "A structured incident summary that blends the backend RCA markdown with the current incident metadata.") }
                <div className="mt-5 space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    {keyValue("Hypothesis", rca.rootCause || detail?.title)}
                    {keyValue("Affected file", rca.affectedFile || detail?.target_app_path)}
                  </div>
                  <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.65)] p-4">
                    <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Executive summary</div>
                    <p className="mt-3 text-sm leading-6 text-[var(--text-primary)]">
                      {rca.summary || detail?.description || "Awaiting root cause synthesis from the backend."}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.65)] p-4">
                    <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Remediation notes</div>
                    <p className="mt-3 text-sm leading-6 text-[var(--text-primary)]">
                      {rca.remediation || "The patch report will appear here once the fix is generated and validated."}
                    </p>
                  </div>
                  {rca.bullets.length ? (
                    <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                      {rca.bullets.slice(0, 4).map((bullet) => (
                        <li key={bullet} className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.65)] px-4 py-3">
                          {bullet}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </article>

              <article className={panelClass()}>
                {sectionTitle("Validation Results View", "Read the gate that decides whether the patch loops back or proceeds to the MR stage.") }
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  {keyValue("Strategy", detail?.validation_strategy)}
                  {keyValue("Outcome", detail?.status === "RESOLVED" ? "Passed" : detail?.status === "WAITING_FOR_RETRY" ? "Retry" : "Pending")}
                  {keyValue("Patch", detail?.patch_diff ? "Generated" : "Missing")}
                </div>
                <div className="mt-5 space-y-3">
                  {validationLogs.length ? (
                    validationLogs.slice(-4).map((log) => (
                      <div key={log.id} className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.65)] p-4">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-xs uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Validation Service</span>
                          <span className={cx("text-xs font-medium uppercase tracking-[0.16em]", severityTone(log.level))}>
                            {severityLabel(log.level)}
                          </span>
                        </div>
                        <p className="mt-3 text-sm leading-6 text-[var(--text-primary)]">{log.message}</p>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.65)] p-5 text-sm text-[var(--text-secondary)]">
                      Validation output will populate after the incident reaches the testing stage.
                    </div>
                  )}
                </div>
              </article>

              <article className={panelClass("xl:col-span-2")}>
                {sectionTitle("Patch Diff Viewer", "The exact source delta generated by the backend. Additions, removals, and context are shown inline.") }
                <div className="mt-5 flex flex-wrap gap-3 text-sm text-[var(--text-secondary)]">
                  <span className={badge(detail?.patch_diff ? "RESOLVED" : "WAITING_FOR_RETRY")}>
                    +{diffStats.additions} / -{diffStats.removals}
                  </span>
                  <span className={badge(detail?.status)}>{detail?.status || "No patch loaded"}</span>
                </div>
                <div className="code-panel mt-5 overflow-hidden rounded-[24px]">
                  <div className="flex items-center justify-between border-b border-[color:var(--border-subtle)] px-4 py-3 text-xs uppercase tracking-[0.18em] text-[var(--text-tertiary)]">
                    <span>{rca.affectedFile || detail?.target_app_path || "patch.diff"}</span>
                    <span>{detail?.confidence_score ? `${detail.confidence_score}% confidence` : "patch preview"}</span>
                  </div>
                  <pre className="max-h-[420px] overflow-auto px-4 py-4 text-sm leading-6 text-[var(--text-primary)]">
                    {detail?.patch_diff ? (
                      detail.patch_diff.split("\n").map((line, index) => {
                        const tone =
                          line.startsWith("+")
                            ? "text-[var(--status-success)]"
                            : line.startsWith("-")
                              ? "text-[var(--status-error)]"
                              : "text-[var(--text-secondary)]";
                        return (
                          <div key={`${index}-${line}`} className={cx("font-[var(--font-mono)]", tone)}>
                            {line || " "}
                          </div>
                        );
                      })
                    ) : (
                      <div className="text-[var(--text-secondary)]">
                        No patch is attached yet. Once the backend reaches patch generation, the unified diff will appear here.
                      </div>
                    )}
                  </pre>
                </div>
              </article>

              <article className={panelClass()}>
                {sectionTitle("Merge Request View", "The remediation handoff: branch, MR URL, and the state of the review gate.") }
                <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  {keyValue("MR URL", detail?.gitlab_mr_url)}
                  {keyValue("Branch", detail?.status === "RESOLVED" ? "created during remediation" : "waiting for MR stage")}
                  {keyValue("Confidence", detail?.confidence_score ? `${detail.confidence_score}%` : "—")}
                  {keyValue("Status", detail?.status)}
                </div>
                <div className="mt-5 rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,11,20,0.65)] p-5">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Review gate</div>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                        The merge request becomes the final human checkpoint after validation. If the run checkpointed, resume the incident first.
                      </p>
                    </div>
                    {detail?.gitlab_mr_url ? (
                      <a
                        href={detail.gitlab_mr_url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-full bg-[color:var(--text-primary)] px-4 py-2 text-sm font-semibold text-[color:var(--surface-base)] transition hover:bg-[rgba(244,247,251,0.92)]"
                      >
                        View MR on GitLab
                      </a>
                    ) : (
                      <span className={badge(detail?.status)}>{detail?.status === "RESOLVED" ? "MR created" : "MR pending"}</span>
                    )}
                  </div>
                </div>
              </article>
            </section>

            <section className="grid gap-6 xl:grid-cols-3">
              <article className={panelClass()}>
                {sectionTitle("Repository Context", "The deterministic context layer used before patch generation.") }
                <div className="mt-5 space-y-3">
                  {keyValue("Repository", detail?.target_repo)}
                  {keyValue("Branch", detail?.target_branch)}
                  {keyValue("Application path", detail?.target_app_path)}
                  {keyValue("Log path", detail?.application_log_path)}
                </div>
              </article>

              <article className={panelClass()}>
                {sectionTitle("CI/CD Snapshot", "The selected pipeline and trace that feed the evidence fusion step.") }
                <div className="mt-5 space-y-3">
                  {keyValue("Pipeline status", detail?.selected_pipeline_status)}
                  {keyValue("Pipeline SHA", detail?.selected_pipeline_sha)}
                  {keyValue("Pipeline URL", detail?.selected_pipeline_web_url)}
                  {keyValue("Validation logs", cicdLogs.at(-1)?.message || "Awaiting pipeline evidence")}
                </div>
              </article>

              <article className={panelClass()}>
                {sectionTitle("Current Incident", "Quick context for the live demo.") }
                <div className="mt-5 space-y-3">
                  {keyValue("Ticket", selectedIncident?.ticket_id)}
                  {keyValue("Module", selectedIncident?.module)}
                  {keyValue("Validation", selectedIncident?.validation_strategy)}
                  {keyValue("Updated", formatTimestamp(selectedIncident?.updated_at))}
                </div>
              </article>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
