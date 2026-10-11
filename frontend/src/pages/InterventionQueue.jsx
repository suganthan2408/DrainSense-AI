import React, { useEffect, useState, useCallback } from "react";
import {
  fetchInterventions, updateInterventionStatus, runAgentExplain,
} from "../api";
import RiskBadge from "../components/RiskBadge";
import { useLocationScope } from "../LocationContext";

const STATUS_COLORS = {
  PENDING: "badge-moderate",
  ASSIGNED: "badge-low",
  COMPLETED: "badge-low",
  VERIFIED: "badge-low",
  CANCELLED: "badge-unknown",
};

const URGENCY_COLORS = {
  LOW: "var(--urgency-low)",
  MEDIUM: "var(--urgency-medium)",
  HIGH: "var(--urgency-high)",
  CRITICAL: "var(--urgency-critical)",
};

export default function InterventionQueue() {
  const [items, setItems] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [agentRunning, setAgentRunning] = useState(null);
  const [agentResults, setAgentResults] = useState({});
  const [updatingId, setUpdatingId] = useState(null);
  const { locationParams, scopeLabel } = useLocationScope();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInterventions({
        ...locationParams,
        ...(statusFilter ? { status: statusFilter } : {}),
      });
      setItems(data.results || data);
    } catch (e) {
      setError("Failed to load interventions: " + e.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, locationParams]);

  useEffect(() => { load(); }, [load]);

  const handleStatusChange = async (item, newStatus) => {
    setUpdatingId(item.id);
    setError(null);
    try {
      const updated = await updateInterventionStatus(item.id, newStatus, "", "");
      setItems((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
    } catch (e) {
      setError("Status update failed: " + (e.response?.data?.error || e.message));
    } finally {
      setUpdatingId(null);
    }
  };

  const handleAgentExplain = async (item) => {
    setAgentRunning(item.id);
    setError(null);
    try {
      const result = await runAgentExplain(item.id);
      setAgentResults((prev) => ({ ...prev, [item.id]: result }));
    } catch (e) {
      setError("Agent failed: " + (e.response?.data?.error || e.message));
    } finally {
      setAgentRunning(null);
    }
  };

  const criticalCount = items.filter((i) => i.urgency === "CRITICAL").length;
  const highCount = items.filter((i) => i.urgency === "HIGH").length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Intervention Priority Queue</h1>
          <p className="page-subtitle">
            {scopeLabel} · Zones ranked by heuristic risk, confidence, and urgency
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem" }}
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            <option value="PENDING">Pending</option>
            <option value="ASSIGNED">Assigned</option>
            <option value="COMPLETED">Completed</option>
            <option value="VERIFIED">Verified</option>
          </select>
          <button className="btn btn-secondary" onClick={load}>↻ Refresh</button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Stats */}
      {items.length > 0 && (
        <div className="grid-4" style={{ marginBottom: "1rem" }}>
          <div className="stat-card"><div className="stat-label">Total</div><div className="stat-value">{items.length}</div></div>
          <div className="stat-card"><div className="stat-label">Critical</div><div className="stat-value" style={{ color: "var(--risk-critical)" }}>{criticalCount}</div></div>
          <div className="stat-card"><div className="stat-label">High</div><div className="stat-value" style={{ color: "var(--risk-high)" }}>{highCount}</div></div>
          <div className="stat-card"><div className="stat-label">Pending</div><div className="stat-value">{items.filter((i) => i.status === "PENDING").length}</div></div>
        </div>
      )}

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading queue…</span></div>
      ) : items.length === 0 ? (
        <div className="card" style={{ textAlign: "center" }}>
          <p className="text-muted" style={{ margin: "2rem 0" }}>
            No interventions found. Run risk assessments from the map or zone detail pages.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {items.map((item) => {
            const urgencyColor = URGENCY_COLORS[item.urgency] || "var(--color-text-muted)";
            const isExpanded = expandedId === item.id;
            const agentResult = agentResults[item.id];

            return (
              <div key={item.id} className="card" style={{ borderLeft: `3px solid ${urgencyColor}` }}>
                {/* Header row */}
                <div
                  style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", cursor: "pointer" }}
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && setExpandedId(isExpanded ? null : item.id)}
                  aria-expanded={isExpanded}
                  aria-label={`Intervention ${item.priority_rank}: ${item.zone_name}`}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: "50%",
                      background: urgencyColor, color: "#000",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontWeight: 700, fontSize: "0.9rem", flexShrink: 0,
                    }}>
                      {item.priority_rank}
                    </div>
                    <div>
                      <div style={{ fontWeight: 700 }}>{item.zone_name}</div>
                      <div className="text-muted text-sm mono">
                        {item.zone_code} · {item.district_name || "District not assigned"}{item.state_name ? `, ${item.state_name}` : ""}
                      </div>
                      {item.zone_is_synthetic && <div className="text-sm" style={{ color: "var(--risk-moderate)" }}>Synthetic demonstration zone</div>}
                      <div className="text-sm" style={{ marginTop: 2 }}>
                        {item.action_display} · Score: {item.priority_score?.toFixed(1)}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "6px", alignItems: "center", flexShrink: 0 }}>
                    <span className={`badge ${STATUS_COLORS[item.status] || "badge-unknown"}`}>{item.status_display}</span>
                    <RiskBadge category={item.urgency} />
                    <span style={{ color: "var(--color-text-muted)", fontSize: "1rem" }}>{isExpanded ? "▲" : "▼"}</span>
                  </div>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div style={{ marginTop: "0.75rem", borderTop: "1px solid var(--color-border)", paddingTop: "0.75rem" }}>
                    <div className="grid-2" style={{ gap: "1rem", marginBottom: "0.75rem" }}>
                      <div>
                        <h3 style={{ marginBottom: 4 }}>Reason for Priority</h3>
                        <p className="text-sm">{item.reason}</p>
                        <h3 style={{ marginBottom: 4 }}>Suggested Action</h3>
                        <p className="text-sm">{item.suggested_action_detail}</p>
                        {item.due_by && (
                          <p className="text-sm text-muted">Due: {new Date(item.due_by).toLocaleString()}</p>
                        )}
                      </div>
                      <div>
                        <h3 style={{ marginBottom: 4 }}>Supporting Evidence</h3>
                        {item.supporting_evidence?.length > 0 ? (
                          <ul style={{ margin: 0, paddingLeft: 16 }} aria-label="Supporting evidence">
                            {item.supporting_evidence.map((e, i) => (
                              <li key={i} className="text-sm" style={{ marginBottom: 4 }}>
                                <strong>{e.description}</strong>: {e.value}
                                <span className="text-muted"> ({e.source})</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-muted text-sm">No evidence linked.</p>
                        )}
                      </div>
                    </div>

                    {/* Agent result */}
                    {agentResult && (
                      <div className="card" style={{ background: "var(--color-bg)", marginBottom: "0.75rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                          <h3 style={{ margin: 0 }}>🤖 Agent Explanation</h3>
                          <span className={`badge ${agentResult.execution_status === "success" ? "badge-low" : "badge-moderate"}`}>
                            {agentResult.execution_status === "success"
                              ? `${agentResult.model_provider || "Model"} execution succeeded`
                              : "Deterministic fallback"}
                          </span>
                        </div>
                        <p className="text-sm">{agentResult.risk_summary}</p>
                        <div className="text-sm">
                          <strong>Execution:</strong> {agentResult.execution_status || "not reported"}
                          {agentResult.model_used && <> · <strong>Model:</strong> {agentResult.model_used}</>}<br />
                          <strong>Recommended:</strong> {agentResult.recommended_action}<br />
                          <strong>Urgency:</strong> {agentResult.urgency} ·{" "}
                          <strong>Human verification:</strong> {agentResult.human_verification_required ? "Required ⚠" : "Not required"}
                        </div>
                        {agentResult.fallback_reason && (
                          <p className="text-sm text-muted" style={{ marginTop: 4, marginBottom: 0 }}>
                            Note: {agentResult.fallback_reason}
                          </p>
                        )}
                      </div>
                    )}

                    {/* Audit log */}
                    {item.logs?.length > 0 && (
                      <div style={{ marginBottom: "0.75rem" }}>
                        <h3 style={{ marginBottom: 4 }}>Status History</h3>
                        {item.logs.map((log) => (
                          <div key={log.id} className="text-sm text-muted" style={{ marginBottom: 2 }}>
                            {new Date(log.logged_at).toLocaleString()} — {log.status_from || "—"} → {log.status_to}
                            {log.notes && ` (${log.notes})`}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Actions */}
                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                      {item.status === "PENDING" && (
                        <button
                          className="btn btn-primary"
                          onClick={() => handleStatusChange(item, "ASSIGNED")}
                          disabled={updatingId === item.id}
                        >
                          Assign
                        </button>
                      )}
                      {item.status === "ASSIGNED" && (
                        <button
                          className="btn btn-primary"
                          onClick={() => handleStatusChange(item, "COMPLETED")}
                          disabled={updatingId === item.id}
                        >
                          Mark Completed
                        </button>
                      )}
                      {item.status === "COMPLETED" && (
                        <button
                          className="btn btn-primary"
                          onClick={() => handleStatusChange(item, "VERIFIED")}
                          disabled={updatingId === item.id}
                        >
                          Verify
                        </button>
                      )}
                      <button
                        className="btn btn-secondary"
                        onClick={() => handleAgentExplain(item)}
                        disabled={agentRunning === item.id}
                        aria-busy={agentRunning === item.id}
                      >
                        {agentRunning === item.id ? <><div className="spinner" style={{ width: 14, height: 14 }} />Running…</> : "🤖 Agent Explain"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
