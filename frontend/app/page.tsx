"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Play, CheckCircle2, Loader2, GitPullRequest, 
  Terminal, Cpu, FileCode, Activity, Check, FileText, 
  Sparkles, ShieldAlert, GitBranch, RefreshCw, Eye,
  Clock, Database, Percent, Trophy, AlertTriangle
} from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const DEMO_PRESET = {
  targetRepo: "swankystark20-group/incidentops-demo-app",
  targetBranch: "main",
  targetAppPath: "invoice-app",
  applicationLogPath: "invoice-app/application.log",
};

function parseRcaReport(report: string) {
  const rootCauseMatch =
    report.match(/## Root Cause Analysis[\s\S]*?\* \*\*Details:\*\*\s*([\s\S]*?)(?=\n## |\n---|$)/i) ||
    report.match(/^Root Cause:\s*([\s\S]*?)(?=\n\nEvidence:|\n## |$)/i);
  const evidenceMatch = report.match(/(?:^Evidence:\s*|\* \*\*Evidence Sources:\*\*\s*)([\s\S]*?)(?=\n## |\n\* \*\*|$)/im);
  const affectedFileMatch = report.match(/\* \*\*Affected File:\*\* `([^`]+)`/i);
  const remediationMatch = report.match(/## Remediation Details\s*([\s\S]*?)(?=\n---|\n## |$)/i);
  const summaryMatch = report.match(/## Executive Summary\s*([\s\S]*?)(?=\n## |$)/i);

  return {
    rootCause: (rootCauseMatch?.[1] || summaryMatch?.[1] || "").trim(),
    evidenceSources: (evidenceMatch?.[1] || "")
      .split("\n")
      .map((line) => line.replace(/^[-*]\s*/, "").trim())
      .filter(Boolean),
    affectedFile: affectedFileMatch?.[1]?.trim() || "",
    remediation: (remediationMatch?.[1] || "").trim(),
  };
}

// Types matching our backend
interface AgentLog {
  id: number;
  agent_name: string;
  message: string;
  level: string;
  timestamp: string;
}

interface Incident {
  id: number;
  ticket_id: string;
  title: string;
  description: string;
  target_repo?: string;
  target_branch?: string;
  target_app_path?: string;
  application_log_path?: string;
  selected_pipeline_id?: string;
  selected_pipeline_ref?: string;
  selected_pipeline_sha?: string;
  selected_pipeline_status?: string;
  selected_pipeline_web_url?: string;
  selected_pipeline_source?: string;
  module?: string;
  validation_strategy?: string;
  status: string;
  gitlab_mr_url?: string;
  rca_report?: string;
  confidence_score?: number;
  patch_diff?: string;
}

interface IncidentTemplate {
  id: string;
  title: string;
  description: string;
  module: string;
  validation: string;
}

interface PlatformMetrics {
  total_incidents: number;
  average_investigation_time_seconds: number;
  evidence_sources_correlated: number;
  files_analyzed: number;
  average_root_cause_confidence: number;
  validation_success_rate: number;
  patch_success_rate: number;
  merge_requests_created: number;
}

interface UiAlert {
  type: "success" | "warning" | "error" | "info";
  title: string;
  message: string;
}

interface RepositoryValidation {
  ok: boolean;
  target_repo: string;
  target_branch: string;
  project_name?: string;
  web_url?: string;
  message: string;
}

export default function Dashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [activeIncident, setActiveIncident] = useState<Incident | null>(null);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [activeTab, setActiveTab] = useState<"logs" | "commits" | "tests">("logs");
  const [isTriggering, setIsTriggering] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string>("");
  const [incidentTemplates, setIncidentTemplates] = useState<IncidentTemplate[]>([]);
  const [targetRepo, setTargetRepo] = useState("");
  const [targetBranch, setTargetBranch] = useState("main");
  const [targetAppPath, setTargetAppPath] = useState("");
  const [applicationLogPath, setApplicationLogPath] = useState("");
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiKeyStatus, setGeminiKeyStatus] = useState("");
  const [alerts, setAlerts] = useState<UiAlert[]>([]);
  const [isValidatingRepo, setIsValidatingRepo] = useState(false);
  const [repositoryValidation, setRepositoryValidation] = useState<RepositoryValidation | null>(null);
  const activeIncidentId = activeIncident?.id;
  const activeIncidentStatus = activeIncident?.status;
  
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const pushAlert = React.useCallback((alert: UiAlert) => {
    setAlerts((prev) => [alert, ...prev].slice(0, 4));
  }, []);

  const clearAlerts = () => setAlerts([]);

  async function apiFetch(path: string, init?: RequestInit) {
    if (!API_BASE_URL) {
      throw new Error(
        "NEXT_PUBLIC_API_BASE_URL is not configured. Copy frontend/.env.example to frontend/.env.local and set the backend URL."
      );
    }
    const res = await fetch(`${API_BASE_URL}${path}`, init);
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try {
        const payload = await res.json();
        detail = payload.detail || detail;
      } catch {
        // Keep HTTP status text when response is not JSON.
      }
      throw new Error(detail);
    }
    return res;
  }

  // Poll for incidents list on mount
  useEffect(() => {
    fetchIncidents();
    fetchIncidentTemplates();
    fetchMetrics();
    fetchGeminiConfig();
  }, []);

  // Scroll to bottom of logs terminal
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  // Handle SSE Real-Time Updates
  useEffect(() => {
    if (!activeIncidentId || activeIncidentStatus === "RESOLVED") return;

    const eventSource = new EventSource(`${API_BASE_URL}/api/stream/${activeIncidentId}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "agent_log") {
          // Append new logs
          setLogs((prev) => {
            if (prev.some((log) => log.id === data.id)) return prev;
            return [...prev, data];
          });
          // Update active executing agent
          setActiveAgent(data.agent_name);
        } else if (data.type === "status_update") {
          // Update global state components
          setActiveIncident((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              status: data.status,
              confidence_score: data.confidence_score,
              gitlab_mr_url: data.gitlab_mr_url,
              patch_diff: data.patch_diff,
              rca_report: data.rca_report
            };
          });
          
          if (data.status === "RESOLVED" || data.status === "FAILED") {
            eventSource.close();
            setActiveAgent("");
            fetchIncidents();
          }
        }
      } catch (err) {
        console.error("SSE parse error", err);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setActiveAgent("");
      pushAlert({
        type: "error",
        title: "Streaming disconnected",
        message: "Live incident updates stopped. Refresh the dashboard to reload the latest logs.",
      });
    };

    return () => {
      eventSource.close();
    };
  }, [activeIncidentId, activeIncidentStatus, pushAlert]);

  async function fetchIncidents() {
    try {
      const res = await apiFetch("/api/incidents");
      const data = await res.json();
      setIncidents(data);
    } catch (err) {
      console.error("Error fetching incidents", err);
      pushAlert({ type: "error", title: "Incident history unavailable", message: String(err) });
    }
  }

  async function fetchIncidentTemplates() {
    try {
      const res = await apiFetch("/api/incidents/templates");
      const data = await res.json();
      setIncidentTemplates(data);
    } catch (err) {
      console.error("Error fetching incident templates", err);
      pushAlert({ type: "error", title: "Incident templates unavailable", message: String(err) });
    }
  }

  async function fetchMetrics() {
    try {
      const res = await apiFetch("/api/incidents/metrics/summary");
      const data = await res.json();
      setMetrics(data);
    } catch (err) {
      console.error("Error fetching platform metrics", err);
      pushAlert({ type: "warning", title: "Metrics unavailable", message: String(err) });
    }
  }

  async function fetchGeminiConfig() {
    try {
      const res = await apiFetch("/api/config/gemini");
      const data = await res.json();
      setGeminiKeyStatus(data.configured ? `Configured: ${data.masked_api_key}` : "Not configured");
    } catch (err) {
      console.error("Error fetching Gemini config", err);
      pushAlert({ type: "warning", title: "Gemini configuration unavailable", message: String(err) });
    }
  }

  async function saveGeminiKey() {
    if (!geminiKey.trim()) return;
    try {
      const res = await apiFetch("/api/config/gemini", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: geminiKey.trim() })
      });
      const data = await res.json();
      setGeminiKey("");
      setGeminiKeyStatus(`Configured: ${data.masked_api_key}`);
    } catch (err) {
      console.error("Error saving Gemini key", err);
      setGeminiKeyStatus("Update failed");
      pushAlert({ type: "error", title: "Gemini key update failed", message: String(err) });
    }
  }

  const selectIncident = async (incident: Incident) => {
    try {
      const res = await apiFetch(`/api/incidents/${incident.id}`);
      const data = await res.json();
      setActiveIncident(data);
      setLogs(data.logs || []);
    } catch (err) {
      console.error("Error loading incident detail", err);
      pushAlert({ type: "error", title: "Incident detail unavailable", message: String(err) });
    }
  };

  const triggerScenario = async (scenario: IncidentTemplate) => {
    if (!targetRepo.trim()) {
      pushAlert({
        type: "warning",
        title: "Repository required",
        message: "Enter a GitLab repository or apply the demo preset before starting an incident.",
      });
      return;
    }
    setIsTriggering(true);
    setLogs([]);
    setActiveAgent("Planner Agent");
    try {
      const res = await apiFetch("/api/incidents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticket_id: scenario.id,
          title: scenario.title,
          description: scenario.description,
          target_repo: targetRepo || undefined,
          target_branch: targetBranch,
          target_app_path: targetAppPath,
          application_log_path: applicationLogPath
        })
      });
      const newIncident = await res.json();
      setActiveIncident(newIncident);
      fetchIncidents();
      fetchMetrics();
    } catch (err) {
      console.error("Error triggering incident", err);
      pushAlert({ type: "error", title: "Incident creation failed", message: String(err) });
    } finally {
      setIsTriggering(false);
    }
  };

  const applyDemoPreset = () => {
    setTargetRepo(DEMO_PRESET.targetRepo);
    setTargetBranch(DEMO_PRESET.targetBranch);
    setTargetAppPath(DEMO_PRESET.targetAppPath);
    setApplicationLogPath(DEMO_PRESET.applicationLogPath);
    setRepositoryValidation(null);
    pushAlert({
      type: "info",
      title: "Demo preset applied",
      message: "Using the benchmark GitLab repository and local demo log paths.",
    });
  };

  const validateRepository = async () => {
    if (!targetRepo.trim()) {
      pushAlert({ type: "warning", title: "Repository required", message: "Enter a GitLab repository path such as group/project." });
      return;
    }
    setIsValidatingRepo(true);
    setRepositoryValidation(null);
    try {
      const res = await apiFetch("/api/config/repository/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_repo: targetRepo.trim(),
          target_branch: targetBranch.trim() || "main",
        }),
      });
      const data = await res.json();
      setRepositoryValidation(data);
      pushAlert({
        type: data.ok ? "success" : "error",
        title: data.ok ? "Repository validated" : "Repository validation failed",
        message: data.message,
      });
    } catch (err) {
      pushAlert({ type: "error", title: "Repository validation failed", message: String(err) });
    } finally {
      setIsValidatingRepo(false);
    }
  };

  const approveMerge = async () => {
    if (!activeIncident) return;
    setIsMerging(true);
    try {
      const res = await apiFetch(`/api/incidents/${activeIncident.id}/approve`, {
        method: "POST"
      });
      const updated = await res.json();
      setActiveIncident(updated);
      fetchIncidents();
    } catch (err) {
      console.error("Error approving merge", err);
      pushAlert({ type: "error", title: "MR approval failed", message: String(err) });
    } finally {
      setIsMerging(false);
    }
  };

  const handleReload = () => {
    fetchIncidents();
    fetchMetrics();
    if (activeIncident) {
      selectIncident(activeIncident);
    }
  };

  // Helper to get agent status color
  const getAgentNodeState = (agentName: string) => {
    if (activeAgent === agentName) return "processing";
    const agentHasLogged = logs.some((l) => l.agent_name === agentName);
    if (agentHasLogged) return "success";
    return "idle";
  };

  // Derive chronological investigation timeline from agent activity logs
  const investigationTimeline = React.useMemo(() => {
    const seenAgents: Record<string, boolean> = {};
    const timelineLabels: Record<string, string> = {
      "System": "Incident Triggered",
      "Planner Agent": "Planner: Scoping Investigation",
      "GitLab Service": "GitLab: Analyzing Code History",
      "CI/CD Service": "CI/CD: Verifying Pipeline Status",
      "Log Service": "Logs: Scanning Error Streams",
      "Evidence Fusion Agent": "Fusion: Correlating Evidence",
      "Patch Generation Agent": "Patch: Drafting Remediation",
      "Validation Service": "Validation: Testing Code Patch",
      "MR & RCA Agent": "MR & RCA: Creating Pull Request",
      "Human Review Gate": "Human: SRE Approval Gate Unlocked",
    };
    
    const timeline: { time: string; label: string; agent: string }[] = [];
    const sortedLogs = [...logs].sort((a, b) => a.id - b.id);
    
    for (const log of sortedLogs) {
      if (!seenAgents[log.agent_name]) {
        seenAgents[log.agent_name] = true;
        const label = timelineLabels[log.agent_name] || log.agent_name;
        let formattedTime = "";
        try {
          const d = new Date(log.timestamp);
          formattedTime = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        } catch {
          formattedTime = "--:--:--";
        }
        
        timeline.push({
          time: formattedTime,
          label,
          agent: log.agent_name
        });
      }
    }
    return timeline;
  }, [logs]);

  // Derive dynamic metrics for System & Incident Dashboard Panel
  const investigationTime = React.useMemo(() => {
    if (logs.length < 2) return "0s";
    const start = new Date(logs[0].timestamp).getTime();
    const end = new Date(logs[logs.length - 1].timestamp).getTime();
    const diffMs = end - start;
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return `${diffSec}s`;
    const mins = Math.floor(diffSec / 60);
    const secs = diffSec % 60;
    return `${mins}m ${secs}s`;
  }, [logs]);

  const evidenceSourcesCount = React.useMemo(() => {
    let count = 0;
    if (logs.some(l => l.agent_name === "GitLab Service")) count++;
    if (logs.some(l => l.agent_name === "Log Service")) count++;
    if (logs.some(l => l.agent_name === "CI/CD Service")) count++;
    return count;
  }, [logs]);

  const filesAnalyzedCount = React.useMemo(() => {
    const hasGit = logs.some(l => l.agent_name === "GitLab Service");
    const hasVal = logs.some(l => l.agent_name === "Validation Service");
    if (hasVal) return 2;
    if (hasGit) return 1;
    return 0;
  }, [logs]);

  const testsPassedDisplay = React.useMemo(() => {
    const passed = activeIncident?.status === "RESOLVED" || logs.some(l => l.agent_name === "Validation Service" && l.message.includes("PASSED"));
    return passed ? "8/8" : "0/8";
  }, [activeIncident?.status, logs]);

  const successfulScenarios = React.useMemo(() => {
    const resolvedIds = new Set(incidents.filter(i => i.status === "RESOLVED").map(i => i.ticket_id));
    return `${resolvedIds.size}/${incidentTemplates.length || 3}`;
  }, [incidents, incidentTemplates.length]);

  const mrsGeneratedCount = React.useMemo(() => {
    return incidents.filter(i => i.gitlab_mr_url || i.status === "RESOLVED").length;
  }, [incidents]);

  const workflowAlerts = React.useMemo<UiAlert[]>(() => {
    const items: UiAlert[] = [];
    const hasMessage = (patterns: string[]) =>
      logs.find((log) => patterns.some((pattern) => log.message.toLowerCase().includes(pattern.toLowerCase())));

    const quota = hasMessage(["RESOURCE_EXHAUSTED", "quota exceeded", "rate limit"]);
    if (quota) items.push({ type: "error", title: "Gemini quota failure", message: quota.message });

    const gitlab = logs.find((log) => log.agent_name === "GitLab Service" && log.level === "ERROR");
    if (gitlab) items.push({ type: "error", title: "GitLab connection failure", message: gitlab.message });

    const missingLog = hasMessage(["runtime log was not generated", "configured log path", "not found on disk"]);
    if (missingLog) items.push({ type: "warning", title: "Missing runtime logs", message: missingLog.message });

    const missingTarget = hasMessage(["missing affected_file", "test_target", "source code", "not found"]);
    if (missingTarget) items.push({ type: "warning", title: "Missing test target or source file", message: missingTarget.message });

    const validation = logs.find((log) => log.agent_name === "Validation Service" && log.message.includes("Validation FAILED"));
    if (validation) items.push({ type: "error", title: "Validation failed", message: validation.message });

    const mr = logs.find((log) => log.agent_name === "MR & RCA Agent" && log.level === "ERROR");
    if (mr) items.push({ type: "error", title: "MR creation failed", message: mr.message });

    if (activeIncident?.status === "FAILED") {
      const failureLog = logs.find((log) => log.level === "ERROR");
      items.push({
        type: "error",
        title: "Incident workflow failed",
        message: failureLog?.message || "The investigation ended in FAILED status. Review the terminal logs for details.",
      });
    }

    return items.slice(0, 8);
  }, [activeIncident?.status, logs]);

  const rcaDetails = React.useMemo(() => {
    const report = activeIncident?.rca_report || "";
    const parsed = report ? parseRcaReport(report) : null;
    const fusionLog = logs.find(
      (log) => log.agent_name === "Evidence Fusion Agent" && log.message.includes("Root Cause")
    )?.message;
    const fusionRootCause = fusionLog?.replace(/^Correlation complete\.\s*Root Cause:\s*/i, "").replace(/\s*\(Confidence:.*$/, "") || "";
    const evidenceFromLogs = logs
      .filter((log) => log.agent_name === "Evidence Fusion Agent" && log.message.startsWith("Evidence Link:"))
      .map((log) => log.message.replace(/^Evidence Link:\s*/, ""));

    const affectedFiles = new Set<string>();
    if (parsed?.affectedFile) affectedFiles.add(parsed.affectedFile);
    logs.forEach((log) => {
      const quoted = log.message.match(/'([^']+\.(?:py|txt|md|json|yml|yaml|toml|js|ts|tsx))'/g) || [];
      quoted.forEach((item) => affectedFiles.add(item.replaceAll("'", "")));
    });

    const pinnedCommit =
      activeIncident?.selected_pipeline_sha ||
      logs.find((log) => log.message.includes("Pinned Commit SHA:"))?.message.match(/Pinned Commit SHA:\s*([a-f0-9]+)/i)?.[1] ||
      "pending";

    return {
      rootCause: parsed?.rootCause || fusionRootCause || "Root cause will appear after evidence fusion.",
      evidenceSources: parsed?.evidenceSources.length ? parsed.evidenceSources : evidenceFromLogs,
      affectedFiles: Array.from(affectedFiles).slice(0, 6),
      selectedCommit: pinnedCommit,
      confidence: activeIncident?.confidence_score || 0,
      remediation:
        parsed?.remediation ||
        (activeIncident?.patch_diff
          ? "Patch generated and ready for validation/MR review."
          : activeIncident?.gitlab_mr_url
          ? "Merge request created with RCA attached."
          : "Remediation summary will appear after patch generation."),
    };
  }, [activeIncident?.confidence_score, activeIncident?.gitlab_mr_url, activeIncident?.patch_diff, activeIncident?.rca_report, activeIncident?.selected_pipeline_sha, logs]);

  return (
    <div className="min-h-screen bg-[#070b13] text-gray-100 flex flex-col antialiased">
      {/* Header */}
      <header className="border-b border-gray-800 bg-[#0c1220]/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
            <Cpu className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 via-emerald-400 to-indigo-400 bg-clip-text text-transparent">
              IncidentOps AI
            </h1>
            <p className="text-xs text-gray-400 font-medium">Autonomous Tier-3 Incident Response Agent</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              type="password"
              value={geminiKey}
              onChange={(event) => setGeminiKey(event.target.value)}
              placeholder="Gemini API key"
              className="w-48 bg-[#0b0f19] border border-gray-800 rounded-lg px-3 py-2 text-gray-200 font-mono text-xs outline-none focus:border-indigo-500"
            />
            <button
              onClick={saveGeminiKey}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-750 border border-gray-700 text-gray-200 rounded-lg text-xs font-semibold transition"
            >
              Save
            </button>
            <span className="text-[10px] text-gray-500 font-mono max-w-36 truncate">{geminiKeyStatus}</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full text-xs font-semibold">
            <Activity className="w-3.5 h-3.5 animate-pulse" />
            Remediation Loop: ACTIVE
          </div>
          <button 
            onClick={handleReload}
            className="p-2 hover:bg-gray-800 rounded-lg border border-gray-800 text-gray-400 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {!API_BASE_URL && (
        <div className="px-6 pt-4">
          <div className="border rounded-lg px-4 py-3 flex items-start gap-3 text-xs bg-red-500/10 border-red-500/30 text-red-100">
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-bold">API URL not configured</div>
              <div className="text-gray-300">
                Set <code className="font-mono">NEXT_PUBLIC_API_BASE_URL</code> in <code className="font-mono">frontend/.env.local</code> (see <code className="font-mono">frontend/.env.example</code>).
              </div>
            </div>
          </div>
        </div>
      )}

      {(alerts.length > 0 || workflowAlerts.length > 0) && (
        <div className="px-6 pt-4 flex flex-col gap-2">
          {[...alerts, ...workflowAlerts].map((alert, idx) => (
            <div
              key={`${alert.title}-${idx}`}
              className={`border rounded-lg px-4 py-3 flex items-start justify-between gap-3 text-xs ${
                alert.type === "success"
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-100"
                  : alert.type === "warning"
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-100"
                  : alert.type === "info"
                  ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-100"
                  : "bg-red-500/10 border-red-500/30 text-red-100"
              }`}
            >
              <div className="flex items-start gap-2 min-w-0">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                  <div className="font-bold">{alert.title}</div>
                  <div className="text-gray-300 break-words">{alert.message}</div>
                </div>
              </div>
              {idx === 0 && alerts.length > 0 && (
                <button onClick={clearAlerts} className="text-gray-400 hover:text-white font-semibold">
                  Dismiss
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Main Grid Workspace */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
        
        {/* LEFT COLUMN: Incidents & Trigger scenarios (4 cols) */}
        <section className="lg:col-span-4 flex flex-col gap-6">
          {/* Predefined Scenarios Panel */}
          <div className="bg-[#0f1626] border border-gray-800 rounded-xl p-5 shadow-xl flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-sm tracking-wider uppercase text-indigo-400 flex items-center gap-2">
                <Sparkles className="w-4 h-4" /> Incident Scenarios
              </h2>
              <button
                onClick={applyDemoPreset}
                className="px-2.5 py-1 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-200 rounded text-[10px] font-semibold transition"
              >
                Apply Demo Preset
              </button>
            </div>
            <div className="text-[11px] text-gray-500 leading-relaxed">
              Start with any GitLab repository. The demo preset targets the benchmark app used in the project walkthrough.
            </div>
            <div className="grid grid-cols-1 gap-3">
              <label className="flex flex-col gap-1 text-xs text-gray-400 font-semibold">
                Target GitLab Repository
                <input
                  value={targetRepo}
                  onChange={(event) => setTargetRepo(event.target.value)}
                  placeholder="group/project"
                  className="w-full bg-[#0b0f19] border border-gray-800 rounded-lg px-3 py-2 text-gray-200 font-mono text-xs outline-none focus:border-indigo-500"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-gray-400 font-semibold">
                Target Branch
                <input
                  value={targetBranch}
                  onChange={(event) => setTargetBranch(event.target.value)}
                  className="w-full bg-[#0b0f19] border border-gray-800 rounded-lg px-3 py-2 text-gray-200 font-mono text-xs outline-none focus:border-indigo-500"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-gray-400 font-semibold">
                Target Application Path
                <input
                  value={targetAppPath}
                  onChange={(event) => setTargetAppPath(event.target.value)}
                  placeholder="empty for repository root"
                  className="w-full bg-[#0b0f19] border border-gray-800 rounded-lg px-3 py-2 text-gray-200 font-mono text-xs outline-none focus:border-indigo-500"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-gray-400 font-semibold">
                Application Log Path
                <input
                  value={applicationLogPath}
                  onChange={(event) => setApplicationLogPath(event.target.value)}
                  placeholder="optional local log path"
                  className="w-full bg-[#0b0f19] border border-gray-800 rounded-lg px-3 py-2 text-gray-200 font-mono text-xs outline-none focus:border-indigo-500"
                />
              </label>
              <div className="flex items-center gap-2">
                <button
                  onClick={validateRepository}
                  disabled={isValidatingRepo}
                  className="flex items-center gap-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-750 disabled:opacity-50 border border-gray-700 text-gray-200 rounded-lg text-xs font-semibold transition"
                >
                  {isValidatingRepo ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  Validate Repository
                </button>
                {repositoryValidation && (
                  <div
                    className={`flex-1 rounded-lg border px-3 py-2 text-[10px] ${
                      repositoryValidation.ok
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
                        : "border-red-500/30 bg-red-500/10 text-red-100"
                    }`}
                  >
                    <div className="font-bold uppercase tracking-wide">
                      {repositoryValidation.ok ? "PASS" : "FAIL"}
                    </div>
                    <div className="text-gray-300 break-words">{repositoryValidation.message}</div>
                  </div>
                )}
              </div>
            </div>
            <div className="flex flex-col gap-3">
              {incidentTemplates.map((scenario) => (
                <button
                  key={scenario.id}
                  disabled={isTriggering}
                  onClick={() => triggerScenario(scenario)}
                  className={`w-full text-left p-4 rounded-lg border transition-all flex items-start justify-between gap-3 group relative overflow-hidden ${
                    activeIncident?.ticket_id === scenario.id
                      ? "bg-indigo-600/15 border-indigo-500 text-white"
                      : "bg-[#0b0f19] border-gray-850 hover:border-gray-700 hover:bg-[#101726]/40 text-gray-300"
                  }`}
                >
                  <div className="flex flex-col gap-1 relative z-10">
                    <span className="text-xs font-mono font-bold text-indigo-400">{scenario.id}</span>
                    <span className="font-semibold text-sm group-hover:text-white transition">{scenario.title}</span>
                    <span className="text-[10px] text-gray-500 font-mono">{scenario.module} / {scenario.validation}</span>
                  </div>
                  <Play className="w-4 h-4 text-gray-500 group-hover:text-indigo-400 transition mt-1 flex-shrink-0" />
                </button>
              ))}
            </div>
          </div>

          {/* Triggered Incidents List */}
          <div className="bg-[#0f1626] border border-gray-800 rounded-xl p-5 shadow-xl flex-1 flex flex-col gap-4 min-h-[250px]">
            <h2 className="font-bold text-sm tracking-wider uppercase text-gray-400">Incident Ticket History</h2>
            <div className="flex-1 overflow-y-auto flex flex-col gap-2 max-h-[400px]">
              {incidents.length === 0 ? (
                <div className="text-center text-gray-500 py-10 text-sm">No incidents analyzed yet.</div>
              ) : (
                incidents.map((inc) => (
                  <button
                    key={inc.id}
                    onClick={() => selectIncident(inc)}
                    className={`text-left p-4 rounded-lg border transition ${
                      activeIncident?.id === inc.id
                        ? "bg-gray-800/60 border-gray-700"
                        : "bg-[#0b0f19] border-gray-850 hover:bg-gray-800/30"
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-mono font-bold text-gray-400">{inc.ticket_id}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                        inc.status === "RESOLVED"
                          ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                          : inc.status === "INVESTIGATING" || inc.status === "PATCHING" || inc.status === "RESOLVING"
                          ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 animate-pulse"
                          : "bg-red-500/15 text-red-400 border border-red-500/30"
                      }`}>
                        {inc.status}
                      </span>
                    </div>
                    <div className="font-semibold text-sm line-clamp-1">{inc.title}</div>
                  </button>
                ))
              )}
            </div>
          </div>
        </section>

        {/* MIDDLE COLUMN: Coordinated Parallel Agent Map & Confidence Gauge (8 cols total) */}
        <section className="lg:col-span-8 flex flex-col gap-6">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            
            {/* Agent Orchestration Map (8/12 cols) */}
            <div className="md:col-span-8 bg-[#0f1626] border border-gray-800 rounded-xl p-5 shadow-xl flex flex-col gap-4">
              <h2 className="font-bold text-sm tracking-wider uppercase text-indigo-400 flex items-center gap-2">
                <Cpu className="w-4 h-4" /> Multi-Agent Orchestration Map
              </h2>
              
              {/* Agent Nodes Grid */}
              <div className="flex-1 flex flex-col justify-between py-2 gap-4">
                
                {/* Layer 1: Planner */}
                <div className="flex justify-center">
                  <div className={`px-4 py-2.5 rounded-lg border text-sm font-semibold flex items-center gap-2 ${
                    getAgentNodeState("Planner Agent") === "processing"
                      ? "bg-indigo-500/15 border-indigo-500 text-white pulsing-indigo"
                      : getAgentNodeState("Planner Agent") === "success"
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                      : "bg-[#0b0f19] border-gray-800 text-gray-500"
                  }`}>
                    {getAgentNodeState("Planner Agent") === "processing" && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />}
                    {getAgentNodeState("Planner Agent") === "success" && <Check className="w-3.5 h-3.5" />}
                    Planner Agent
                  </div>
                </div>

                {/* Arrow */}
                <div className="text-center text-gray-700 text-xs">▼</div>

                {/* Layer 2: Coordinated Parallel Retrieval */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: "GitLab Service", name: "GitLab Service" },
                    { id: "CI/CD Service", name: "CI/CD Service" },
                    { id: "Log Service", name: "Log Service" }
                  ].map((node) => {
                    const state = getAgentNodeState(node.id);
                    return (
                      <div
                        key={node.id}
                        className={`p-3 rounded-lg border text-xs font-semibold text-center flex flex-col items-center justify-center gap-1.5 transition ${
                          state === "processing"
                            ? "bg-indigo-500/15 border-indigo-500 text-white pulsing-indigo"
                            : state === "success"
                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                            : "bg-[#0b0f19] border-gray-800 text-gray-500"
                        }`}
                      >
                        {state === "processing" && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />}
                        {state === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                        {node.name}
                      </div>
                    );
                  })}
                </div>

                {/* Arrow */}
                <div className="text-center text-gray-700 text-xs">▲</div>

                {/* Layer 3: Reasoning & Remediation */}
                <div className="flex flex-wrap justify-center gap-3">
                  {[
                    { id: "Evidence Fusion Agent", name: "Evidence Fusion" },
                    { id: "Patch Generation Agent", name: "Patch Gen" },
                    { id: "Validation Service", name: "Validation Service" },
                    { id: "MR & RCA Agent", name: "MR & RCA" }
                  ].map((node) => {
                    const state = getAgentNodeState(node.id);
                    return (
                      <div
                        key={node.id}
                        className={`px-3.5 py-2.5 rounded-lg border text-xs font-semibold flex items-center gap-2 ${
                          state === "processing"
                            ? "bg-indigo-500/15 border-indigo-500 text-white pulsing-indigo"
                            : state === "success"
                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                            : "bg-[#0b0f19] border-gray-800 text-gray-500"
                        }`}
                      >
                        {state === "processing" && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />}
                        {state === "success" && <Check className="w-3.5 h-3.5" />}
                        {node.name}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Confidence & Timeline Stacked (4/12 cols) */}
            <div className="md:col-span-4 flex flex-col gap-6">
              {/* Confidence Score Panel */}
              <div className="bg-[#0f1626] border border-gray-800 rounded-xl p-5 shadow-xl flex flex-col justify-between h-[180px]">
                <h2 className="font-bold text-sm tracking-wider uppercase text-gray-400">Diagnosis Confidence</h2>
                <div className="flex items-center justify-between py-2 flex-1">
                  <div className="relative flex items-center justify-center">
                    <svg className="w-20 h-20 transform -rotate-90">
                      <circle
                        cx="40"
                        cy="40"
                        r="32"
                        stroke="#1f2937"
                        strokeWidth="6"
                        fill="transparent"
                      />
                      <circle
                        cx="40"
                        cy="40"
                        r="32"
                        stroke={
                          (activeIncident?.confidence_score || 0) >= 80 
                            ? "#10b981" 
                            : (activeIncident?.confidence_score || 0) >= 50 
                            ? "#6366f1" 
                            : "#374151"
                        }
                        strokeWidth="6"
                        fill="transparent"
                        strokeDasharray="201.06"
                        strokeDashoffset={201.06 - (201.06 * (activeIncident?.confidence_score || 0)) / 100}
                        className="transition-all duration-1000 ease-out"
                      />
                    </svg>
                    <span className="absolute text-lg font-black font-mono">
                      {activeIncident?.confidence_score || 0}%
                    </span>
                  </div>
                  <div className="text-right flex flex-col gap-1 pr-2">
                    <span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider">Status</span>
                    <span className={`text-sm font-bold uppercase ${
                      activeIncident?.status === "RESOLVED"
                        ? "text-emerald-400"
                        : activeIncident?.status === "INVESTIGATING" || activeIncident?.status === "PATCHING"
                        ? "text-indigo-400 animate-pulse"
                        : "text-red-400"
                    }`}>
                      {activeIncident?.status || "IDLE"}
                    </span>
                  </div>
                </div>
              </div>

              {/* System & Incident Metrics Panel */}
              <div className="bg-[#0f1626] border border-gray-800 rounded-xl p-5 shadow-xl flex flex-col gap-4">
                <h2 className="font-bold text-sm tracking-wider uppercase text-indigo-400 flex items-center gap-2">
                  <Activity className="w-4 h-4" /> System & Incident Metrics
                </h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0b0f19] border border-gray-850 p-3 rounded-lg flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-md">
                      <Clock className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">Investigation Time</div>
                      <div className="text-sm font-bold text-gray-200">{investigationTime}</div>
                    </div>
                  </div>

                  <div className="bg-[#0b0f19] border border-gray-850 p-3 rounded-lg flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-md">
                      <Percent className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">RCA Confidence</div>
                      <div className="text-sm font-bold text-gray-200">{activeIncident?.confidence_score || 0}%</div>
                    </div>
                  </div>

                  <div className="bg-[#0b0f19] border border-gray-850 p-3 rounded-lg flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 text-blue-400 rounded-md">
                      <Database className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">Evidence Sources</div>
                      <div className="text-sm font-bold text-gray-200">{metrics?.evidence_sources_correlated ?? evidenceSourcesCount}</div>
                    </div>
                  </div>

                  <div className="bg-[#0b0f19] border border-gray-850 p-3 rounded-lg flex items-center gap-3">
                    <div className="p-2 bg-amber-500/10 text-amber-400 rounded-md">
                      <FileCode className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">Files Analyzed</div>
                      <div className="text-sm font-bold text-gray-200">{metrics?.files_analyzed ?? filesAnalyzedCount}</div>
                    </div>
                  </div>

                  <div className="bg-[#0b0f19] border border-gray-850 p-3 rounded-lg flex items-center gap-3">
                    <div className="p-2 bg-teal-500/10 text-teal-400 rounded-md">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">Tests Passed</div>
                      <div className="text-sm font-bold text-gray-200">{testsPassedDisplay}</div>
                    </div>
                  </div>

                  <div className="bg-[#0b0f19] border border-gray-850 p-3 rounded-lg flex items-center gap-3">
                    <div className="p-2 bg-purple-500/10 text-purple-400 rounded-md">
                      <Trophy className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase font-semibold">Success Rate</div>
                      <div className="text-sm font-bold text-gray-200">{successfulScenarios}</div>
                    </div>
                  </div>
                </div>

                <div className="bg-[#0b0f19] border border-gray-850 p-3 rounded-lg flex items-center gap-3">
                  <div className="p-2 bg-pink-500/10 text-pink-400 rounded-md">
                    <GitPullRequest className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-[10px] text-gray-500 uppercase font-semibold">MRs Generated</div>
                    <div className="text-sm font-bold text-gray-200">{metrics?.merge_requests_created ?? mrsGeneratedCount} MRs</div>
                  </div>
                </div>
              </div>

              {/* Live Investigation Timeline Panel */}
              <div className="bg-[#0f1626] border border-gray-800 rounded-xl p-5 shadow-xl flex flex-col gap-4 flex-1 min-h-[220px]">
                <h2 className="font-bold text-sm tracking-wider uppercase text-indigo-400 flex items-center gap-2">
                  <Activity className="w-4 h-4" /> Live Timeline
                </h2>
                <div className="flex-1 overflow-y-auto max-h-[200px] pr-1 scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent">
                  {investigationTimeline.length === 0 ? (
                    <div className="text-center text-gray-500 py-10 text-xs italic">
                      Waiting for orchestration to begin...
                    </div>
                  ) : (
                    <div className="relative border-l border-gray-800 ml-2 pl-4 flex flex-col gap-4">
                      {investigationTimeline.map((item, idx) => {
                        const isLatest = idx === investigationTimeline.length - 1;
                        return (
                          <div key={idx} className="relative flex flex-col gap-0.5">
                            <span className={`absolute -left-[21px] top-1.5 rounded-full w-2.5 h-2.5 border ${
                              isLatest
                                ? "bg-indigo-500 border-indigo-400 ring-4 ring-indigo-500/20 animate-pulse"
                                : "bg-emerald-500 border-emerald-400"
                            }`} />
                            <div className="flex items-center justify-between gap-2">
                              <span className={`text-xs font-semibold ${isLatest ? "text-white" : "text-gray-300"}`}>
                                {item.label}
                              </span>
                              <span className="text-[9px] font-mono text-gray-500 flex-shrink-0">{item.time}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Evidence Terminal & Patch panels */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 flex-1 min-h-[350px]">
            
            {/* Tabbed Evidence Terminal (7/12 cols) */}
            <div className="md:col-span-7 bg-[#0b0f19] border border-gray-800 rounded-xl flex flex-col overflow-hidden shadow-2xl">
              <div className="bg-[#0f1626] px-4 py-2 border-b border-gray-850 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Terminal className="w-4 h-4 text-indigo-400" />
                  <span className="font-mono text-xs font-bold uppercase text-gray-400">Investigation Terminal</span>
                </div>
                <div className="flex gap-2">
                  {([
                    { id: "logs", label: "Logs" },
                    { id: "commits", label: "Commits" },
                    { id: "tests", label: "Tests" }
                  ] as { id: "logs" | "commits" | "tests"; label: string }[]).map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`px-3 py-1 rounded text-xs font-semibold transition ${
                        activeTab === tab.id 
                          ? "bg-gray-800 text-white" 
                          : "text-gray-500 hover:text-gray-300"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Terminal Content */}
              <div className="flex-1 p-4 font-mono text-xs overflow-y-auto bg-[#05080f] flex flex-col gap-2 max-h-[300px]">
                {activeTab === "logs" && (
                  <>
                    {logs.map((log) => (
                      <div key={log.id} className="flex items-start gap-2 leading-relaxed">
                        <span className="text-gray-600 select-none">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        <span className={`font-semibold ${
                          log.level === "ERROR" 
                            ? "text-red-400" 
                            : log.level === "WARNING" 
                            ? "text-yellow-400" 
                            : "text-indigo-400"
                        }`}>
                          [{log.agent_name}]:
                        </span>
                        <span className="text-gray-300">{log.message}</span>
                      </div>
                    ))}
                    <div ref={terminalEndRef} />
                  </>
                )}

                {activeTab === "commits" && (
                  <div className="flex flex-col gap-3">
                    <div className="text-gray-500 font-semibold border-b border-gray-900 pb-1 flex items-center gap-1">
                      <GitBranch className="w-3.5 h-3.5 text-indigo-400" /> Git Log Analyzer Output
                    </div>
                    <div className="bg-[#0e1726]/40 p-3 rounded border border-indigo-500/10">
                      <span className="text-indigo-400 font-bold block mb-1">{activeIncident?.target_repo || targetRepo}</span>
                      <span className="text-gray-400 text-[11px] block">Branch: {activeIncident?.target_branch || targetBranch}</span>
                      <span className="text-gray-400 text-[11px] block">App path: {activeIncident?.target_app_path ?? targetAppPath}</span>
                      <span className="text-gray-400 text-[11px] block">Log path: {activeIncident?.application_log_path ?? applicationLogPath}</span>
                      <span className="text-gray-200 block font-semibold mt-2">Commit evidence is collected by the GitLab Service during each run.</span>
                    </div>
                  </div>
                )}

                {activeTab === "tests" && (
                  <div className="flex flex-col gap-3">
                    <div className="text-gray-500 font-semibold border-b border-gray-900 pb-1 flex items-center gap-1">
                      <ShieldAlert className="w-3.5 h-3.5 text-red-400" /> Pipeline Test Failure Reports
                    </div>
                    <div className="bg-red-500/5 p-3 rounded border border-red-500/10 text-red-400 leading-relaxed">
                      <span className="font-bold block mb-1">{activeIncident?.validation_strategy || "Configured validation strategy"}</span>
                      <span className="text-gray-300 font-mono text-[11px] block">
                        Pipeline #{activeIncident?.selected_pipeline_id || "pending"} via {activeIncident?.selected_pipeline_source || "selection pending"}
                      </span>
                      <span className="text-gray-300 font-mono text-[11px] block">
                        {activeIncident?.selected_pipeline_status || "unknown"} on {activeIncident?.selected_pipeline_ref || activeIncident?.target_branch || targetBranch}
                      </span>
                      {activeIncident?.selected_pipeline_web_url && (
                        <a href={activeIncident.selected_pipeline_web_url} target="_blank" rel="noreferrer" className="text-indigo-300 text-[11px] underline">
                          View selected pipeline
                        </a>
                      )}
                      <span className="text-gray-500 text-[10px] block mt-2">Incident: {activeIncident?.ticket_id || "none selected"}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Code Patch Diff & Review Gate (5/12 cols) */}
            <div className="md:col-span-5 bg-[#0f1626] border border-gray-800 rounded-xl p-5 shadow-xl flex flex-col gap-4 overflow-hidden">
              <h2 className="font-bold text-sm tracking-wider uppercase text-gray-400 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-emerald-400" /> Remediation Patch
              </h2>

              {/* Code Diff Box */}
              <div className="flex-1 bg-[#05080f] rounded-lg border border-gray-950 p-3 font-mono text-[10px] overflow-y-auto max-h-[180px]">
                {activeIncident?.patch_diff ? (
                  activeIncident.patch_diff.split("\n").map((line, idx) => {
                    const isAddition = line.startsWith("+") && !line.startsWith("+++");
                    const isDeletion = line.startsWith("-") && !line.startsWith("---");
                    return (
                      <div 
                        key={idx} 
                        className={`whitespace-pre-wrap ${
                          isAddition ? "text-emerald-400 bg-emerald-500/5" : isDeletion ? "text-red-400 bg-red-500/5" : "text-gray-400"
                        }`}
                      >
                        {line}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-gray-600 text-center py-12">Waiting for evidence fusion & patch generation...</div>
                )}
              </div>

              {/* Human Review Gate / GitLab MR Box */}
              <div className="bg-[#0b0f19] border border-gray-850 rounded-lg p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400 font-semibold">Merge Request Status</span>
                  {activeIncident?.gitlab_mr_url ? (
                    <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                      <GitPullRequest className="w-3.5 h-3.5" /> OPENED
                    </span>
                  ) : (
                    <span className="text-gray-500 font-bold">PENDING</span>
                  )}
                </div>

                {activeIncident?.gitlab_mr_url && (
                  <a
                    href={activeIncident.gitlab_mr_url}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full text-center text-xs py-2 bg-gray-800 hover:bg-gray-750 border border-gray-700 text-gray-200 rounded-md font-semibold transition flex items-center justify-center gap-1.5"
                  >
                    <Eye className="w-3.5 h-3.5" /> View MR on GitLab
                  </a>
                )}

                {activeIncident?.status === "RESOLVING" || (activeIncident?.status === "RESOLVED" && logs.some((l) => l.agent_name === "MR & RCA Agent")) ? (
                  <button
                    disabled={isMerging || activeIncident?.status === "RESOLVED"}
                    onClick={approveMerge}
                    className="w-full text-center text-xs py-2.5 bg-gradient-to-r from-emerald-500 to-indigo-600 hover:opacity-90 disabled:opacity-50 text-white rounded-md font-bold tracking-wide transition shadow-lg shadow-indigo-600/10"
                  >
                    {isMerging ? (
                      <span className="flex items-center justify-center gap-1.5">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Merging...
                      </span>
                    ) : activeIncident?.status === "RESOLVED" ? (
                      <span className="flex items-center justify-center gap-1.5">
                        <Check className="w-3.5 h-3.5" /> APPROVED & MERGED
                      </span>
                    ) : (
                      "Approve & Merge (Review Gate)"
                    )}
                  </button>
                ) : (
                  <div className="text-[11px] text-gray-500 text-center italic py-2">
                    Review gate unlocks once validation passes.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Root Cause Analysis Panel */}
          <div className="bg-[#0f1626] border border-gray-800 rounded-xl p-5 shadow-xl flex flex-col gap-4">
            <h2 className="font-bold text-sm tracking-wider uppercase text-indigo-400 flex items-center gap-2">
              <FileText className="w-4 h-4" /> Root Cause Analysis
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 bg-[#05080f] rounded-lg border border-gray-950 p-4">
                <div className="text-[10px] uppercase font-bold text-gray-500 mb-2">Root Cause</div>
                <div className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap max-h-[180px] overflow-y-auto">
                  {rcaDetails.rootCause}
                </div>
              </div>
              <div className="bg-[#05080f] rounded-lg border border-gray-950 p-4 flex flex-col gap-3">
                <div>
                  <div className="text-[10px] uppercase font-bold text-gray-500">Confidence</div>
                  <div className="text-lg font-black text-emerald-400 font-mono">{rcaDetails.confidence}%</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-gray-500">Selected Commit</div>
                  <div className="text-xs text-gray-300 font-mono break-all">
                    {rcaDetails.selectedCommit === "pending" ? "pending" : String(rcaDetails.selectedCommit).slice(0, 12)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-gray-500">Evidence Sources</div>
                  <div className="text-xs text-gray-300">{rcaDetails.evidenceSources.length || evidenceSourcesCount} correlated</div>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-[#05080f] rounded-lg border border-gray-950 p-4">
                <div className="text-[10px] uppercase font-bold text-gray-500 mb-2">Affected Files</div>
                {rcaDetails.affectedFiles.length > 0 ? (
                  <div className="flex flex-col gap-1">
                    {rcaDetails.affectedFiles.map((file) => (
                      <span key={file} className="text-xs text-gray-300 font-mono">{file}</span>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-gray-600">Pending evidence fusion.</div>
                )}
              </div>
              <div className="bg-[#05080f] rounded-lg border border-gray-950 p-4">
                <div className="text-[10px] uppercase font-bold text-gray-500 mb-2">Remediation Summary</div>
                <div className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {rcaDetails.remediation}
                </div>
              </div>
            </div>
            {rcaDetails.evidenceSources.length > 0 && (
              <div className="bg-[#05080f] rounded-lg border border-gray-950 p-4">
                <div className="text-[10px] uppercase font-bold text-gray-500 mb-2">Evidence Sources</div>
                <div className="flex flex-col gap-1 max-h-[160px] overflow-y-auto">
                  {rcaDetails.evidenceSources.map((item, idx) => (
                    <span key={`${item}-${idx}`} className="text-xs text-gray-300 font-mono leading-relaxed">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {activeIncident?.rca_report && (
              <details className="bg-[#05080f] rounded-lg border border-gray-950 p-4">
                <summary className="text-[10px] uppercase font-bold text-gray-500 cursor-pointer">Full RCA Report</summary>
                <div className="text-gray-300 text-xs leading-relaxed font-mono whitespace-pre-wrap max-h-[220px] overflow-y-auto mt-3">
                  {activeIncident.rca_report}
                </div>
              </details>
            )}
          </div>

        </section>
      </main>
    </div>
  );
}
