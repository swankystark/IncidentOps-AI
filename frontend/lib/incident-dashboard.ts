export type IncidentStatus =
  | "INVESTIGATING"
  | "PATCHING"
  | "RESOLVED"
  | "FAILED"
  | "WAITING_FOR_RETRY"
  | string;

export type AgentLog = {
  id: number;
  agent_name: string;
  message: string;
  level: string;
  timestamp: string;
};

export type IncidentSummary = {
  id: number;
  ticket_id: string;
  title: string;
  description: string;
  status: IncidentStatus;
  target_repo?: string;
  target_branch?: string;
  target_app_path?: string;
  application_log_path?: string;
  module?: string;
  validation_strategy?: string;
  selected_pipeline_status?: string;
  selected_pipeline_sha?: string;
  selected_pipeline_web_url?: string;
  selected_pipeline_source?: string;
  confidence_score?: number;
  gitlab_mr_url?: string;
  patch_diff?: string;
  rca_report?: string;
  created_at: string;
  updated_at: string;
};

export type IncidentDetail = IncidentSummary & { logs: AgentLog[] };

export type IncidentTemplate = {
  id: string;
  title: string;
  description: string;
  module: string;
  validation: string;
  target_file?: string;
  test_target?: string;
  priority_signals?: string[];
};

export type PlatformMetrics = {
  total_incidents: number;
  average_investigation_time_seconds: number;
  evidence_sources_correlated: number;
  files_analyzed: number;
  average_root_cause_confidence: number;
  validation_success_rate: number;
  patch_success_rate: number;
  merge_requests_created: number;
};

export type RepositoryValidation = {
  ok: boolean;
  target_repo: string;
  target_branch: string;
  project_name?: string;
  web_url?: string;
  message: string;
};

export type TimelinePhase = {
  key: string;
  label: string;
  summary: string;
  status: "pending" | "running" | "complete" | "warning";
  timestamp?: string;
};

export const workflowPhases = [
  ["planner", "Planner", "Scopes the incident and pulls retrieval signals."],
  ["log_service", "Logs", "Extracts runtime evidence from the application log."],
  ["gitlab_service", "GitLab", "Collects commits, files, and branch context."],
  ["cicd_service", "CI/CD", "Selects the relevant pipeline and job traces."],
  ["evidence_fusion", "Fusion", "Correlates the evidence into a root cause."],
  ["repository_context", "Context", "Adds related files, imports, tests, commits."],
  ["patch_generation", "Patch", "Writes the minimal source fix."],
  ["validation_service", "Validation", "Runs the template-selected check."],
  ["mr_creation", "MR + RCA", "Creates the branch, commit, MR, and report."],
] as const;

const agentToPhase: Record<string, string> = {
  Planner: "planner",
  "Log Service": "log_service",
  "GitLab Service": "gitlab_service",
  "CI/CD Service": "cicd_service",
  "Evidence Fusion Agent": "evidence_fusion",
  "Repository Context": "repository_context",
  "Patch Generation Agent": "patch_generation",
  "Validation Service": "validation_service",
  "MR & RCA Agent": "mr_creation",
};

export function formatTimestamp(value?: string) {
  if (!value) return "just now";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function phaseTone(status: TimelinePhase["status"]) {
  switch (status) {
    case "complete":
      return "border-[color:var(--status-success)]/35 bg-[rgba(74,222,128,0.10)] text-[color:var(--status-success)]";
    case "running":
      return "border-[color:var(--accent-primary)]/45 bg-[rgba(93,214,255,0.10)] text-[color:var(--accent-primary)]";
    case "warning":
      return "border-[color:var(--status-warning)]/35 bg-[rgba(251,191,36,0.12)] text-[color:var(--status-warning)]";
    default:
      return "border-[color:var(--border-subtle)] text-[var(--text-tertiary)]";
  }
}

export function statusTone(status?: string) {
  const value = (status || "INVESTIGATING").toUpperCase();
  if (value.includes("RESOLVED")) {
    return "border-[color:var(--status-success)]/30 bg-[rgba(74,222,128,0.10)] text-[color:var(--status-success)]";
  }
  if (value.includes("WAITING") || value.includes("PATCH")) {
    return "border-[color:var(--status-warning)]/30 bg-[rgba(251,191,36,0.10)] text-[color:var(--status-warning)]";
  }
  if (value.includes("FAILED")) {
    return "border-[color:var(--status-error)]/30 bg-[rgba(251,113,133,0.10)] text-[color:var(--status-error)]";
  }
  return "border-[color:var(--accent-primary)]/25 bg-[rgba(93,214,255,0.08)] text-[color:var(--accent-primary)]";
}

export function severityTone(level?: string) {
  const value = (level || "INFO").toUpperCase();
  if (value.includes("ERROR")) return "text-[color:var(--status-error)]";
  if (value.includes("WARNING")) return "text-[color:var(--status-warning)]";
  return "text-[var(--text-secondary)]";
}

export function parseRcaReport(report?: string) {
  if (!report) {
    return { summary: "", rootCause: "", remediation: "", affectedFile: "", bullets: [] as string[] };
  }

  const summary = (report.match(/## Executive Summary\s*([\s\S]*?)(?=\n## |\n---|$)/i)?.[1] || "").trim();
  const details = (report.match(/\*\*Details:\*\*\s*([\s\S]*?)(?=\n## |\n---|$)/i)?.[1] || "").trim();
  const remediation = (report.match(/## Remediation Details\s*([\s\S]*?)(?=\n---|$)/i)?.[1] || "").trim();
  const affectedFile = report.match(/\*\*Affected File:\*\* `([^`]+)`/i)?.[1] || "";
  const bullets = report
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("* "))
    .map((line) => line.replace(/^\*\s*/, ""));

  return { summary, rootCause: details, remediation, affectedFile, bullets };
}

export function buildTimeline(detail?: IncidentDetail | null): TimelinePhase[] {
  const phases = workflowPhases.map(([key, label, summary]) => ({
    key,
    label,
    summary,
    status: "pending" as const,
  }));

  if (!detail) {
    return phases;
  }

  const lastLog = detail.logs.at(-1);
  const currentPhase = lastLog ? agentToPhase[lastLog.agent_name] : "";
  const status = detail.status.toUpperCase();
  const hasPatch = Boolean(detail.patch_diff);
  const hasMr = Boolean(detail.gitlab_mr_url);
  const validationPassed = detail.logs.some((log) => log.message.includes("Validation PASSED"));

  return phases.map((phase) => {
    const seen = detail.logs.some((log) => agentToPhase[log.agent_name] === phase.key);
    const running = phase.key === currentPhase && status !== "RESOLVED" && status !== "FAILED";
    let nextStatus: TimelinePhase["status"] = seen ? "complete" : "pending";
    if (running) nextStatus = "running";
    if (phase.key === "validation_service" && !validationPassed && status.includes("WAITING")) {
      nextStatus = "warning";
    }
    if (phase.key === "patch_generation" && !hasPatch && status === "FAILED") {
      nextStatus = "warning";
    }
    if (phase.key === "mr_creation" && hasMr && status === "RESOLVED") {
      nextStatus = "complete";
    }
    return {
      ...phase,
      status: nextStatus,
      timestamp: seen ? detail.logs.find((log) => agentToPhase[log.agent_name] === phase.key)?.timestamp : undefined,
    };
  });
}

export function diffSummary(diff?: string) {
  if (!diff) return { additions: 0, removals: 0 };
  return diff.split("\n").reduce(
    (acc, line) => {
      if (line.startsWith("+")) acc.additions += 1;
      if (line.startsWith("-")) acc.removals += 1;
      return acc;
    },
    { additions: 0, removals: 0 }
  );
}
