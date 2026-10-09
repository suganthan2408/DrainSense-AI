import React, { useEffect, useState, useCallback } from "react";
import { fetchOutcomes, fetchEvaluations, computeEvaluation, fetchZones, recordOutcome, fetchAssessments } from "../api";

export default function OutcomeTracking() {
  const [outcomes, setOutcomes] = useState([]);
  const [evaluations, setEvaluations] = useState([]);
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [form, setForm] = useState({
    zone: "",
    risk_assessment: "",
    outcome: "OCCURRED",
    severity: "MODERATE",
    report_source: "FIELD_REPORT",
    is_synthetic: true,
    recorded_by: "Field Inspector",
    observation_window_start: "",
    observation_window_end: "",
  });
  const [zoneAssessments, setZoneAssessments] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [o, e, z] = await Promise.all([
        fetchOutcomes(),
        fetchEvaluations(),
        fetchZones(),
      ]);
      setOutcomes((o.results || o).slice(0, 20));
      setEvaluations(e.results || e);
      setZones(z.results || z);
    } catch (err) {
      setError("Failed to load: " + err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleZoneChange = async (zoneId) => {
    setForm((f) => ({ ...f, zone: zoneId, risk_assessment: "" }));
    if (zoneId) {
      const data = await fetchAssessments(zoneId);
      setZoneAssessments(data.results || data);
    } else {
      setZoneAssessments([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const now = new Date();
      const payload = {
        ...form,
        zone: parseInt(form.zone),
        risk_assessment: form.risk_assessment ? parseInt(form.risk_assessment) : null,
        observation_window_start: form.observation_window_start || new Date(now.getTime() - 6 * 3600000).toISOString(),
        observation_window_end: form.observation_window_end || now.toISOString(),
      };
      await recordOutcome(payload);
      setSuccess("Outcome recorded successfully.");
      await load();
    } catch (err) {
      setError("Failed to record outcome: " + (err.response?.data ? JSON.stringify(err.response.data) : err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const handleComputeMetrics = async () => {
    setComputing(true);
    setError(null);
    try {
      const result = await computeEvaluation();
      if (result.detail) {
        setError(result.detail);
      } else {
        await load();
        setSuccess("Evaluation metrics computed.");
      }
    } catch (err) {
      setError("Computation failed: " + (err.response?.data?.error || err.message));
    } finally {
      setComputing(false);
    }
  };

  const latestEval = evaluations[0];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Prediction & Outcome Tracking</h1>
          <p className="page-subtitle">Record observed waterlogging outcomes and evaluate prediction accuracy</p>
        </div>
        <button className="btn btn-secondary" onClick={load}>↻ Refresh</button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="grid-2" style={{ gap: "1rem", marginBottom: "1.5rem" }}>
        {/* Record outcome form */}
        <div className="card">
          <h2 style={{ marginBottom: "0.75rem" }}>Record Observed Outcome</h2>
          <form onSubmit={handleSubmit} noValidate aria-label="Record waterlogging outcome">
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <label>
                <div className="text-sm text-muted" style={{ marginBottom: 4 }}>Zone *</div>
                <select
                  required value={form.zone}
                  onChange={(e) => handleZoneChange(e.target.value)}
                  style={{ width: "100%", background: "var(--color-surface2)", border: "1px solid var(--color-border)", color: "var(--color-text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem" }}
                >
                  <option value="">Select zone…</option>
                  {zones.map((z) => <option key={z.id} value={z.id}>{z.name} ({z.code})</option>)}
                </select>
              </label>

              {zoneAssessments.length > 0 && (
                <label>
                  <div className="text-sm text-muted" style={{ marginBottom: 4 }}>Linked Risk Assessment</div>
                  <select
                    value={form.risk_assessment}
                    onChange={(e) => setForm((f) => ({ ...f, risk_assessment: e.target.value }))}
                    style={{ width: "100%", background: "var(--color-surface2)", border: "1px solid var(--color-border)", color: "var(--color-text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem" }}
                  >
                    <option value="">None</option>
                    {zoneAssessments.map((a) => (
                      <option key={a.id} value={a.id}>
                        {new Date(a.assessed_at).toLocaleString()} — {a.risk_category} ({a.risk_score})
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <div className="grid-2" style={{ gap: "0.5rem" }}>
                <label>
                  <div className="text-sm text-muted" style={{ marginBottom: 4 }}>Outcome *</div>
                  <select
                    required value={form.outcome}
                    onChange={(e) => setForm((f) => ({ ...f, outcome: e.target.value }))}
                    style={{ width: "100%", background: "var(--color-surface2)", border: "1px solid var(--color-border)", color: "var(--color-text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem" }}
                  >
                    <option value="OCCURRED">Waterlogging occurred</option>
                    <option value="NOT_OCCURRED">No waterlogging</option>
                    <option value="UNKNOWN">Not verified</option>
                  </select>
                </label>
                <label>
                  <div className="text-sm text-muted" style={{ marginBottom: 4 }}>Severity</div>
                  <select
                    value={form.severity}
                    onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value }))}
                    style={{ width: "100%", background: "var(--color-surface2)", border: "1px solid var(--color-border)", color: "var(--color-text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem" }}
                  >
                    <option value="NONE">None</option>
                    <option value="MINOR">Minor</option>
                    <option value="MODERATE">Moderate</option>
                    <option value="SEVERE">Severe</option>
                  </select>
                </label>
              </div>

              <label>
                <div className="text-sm text-muted" style={{ marginBottom: 4 }}>Report Source</div>
                <select
                  value={form.report_source}
                  onChange={(e) => setForm((f) => ({ ...f, report_source: e.target.value }))}
                  style={{ width: "100%", background: "var(--color-surface2)", border: "1px solid var(--color-border)", color: "var(--color-text)", padding: "6px 10px", borderRadius: "var(--radius)", fontSize: "0.875rem" }}
                >
                  <option value="FIELD_REPORT">Field inspector report</option>
                  <option value="CITIZEN_REPORT">Citizen report</option>
                  <option value="NEWS_REPORT">News/media report</option>
                  <option value="SENSOR">Sensor reading</option>
                  <option value="SYNTHETIC_DEMO">Synthetic demonstration</option>
                </select>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  type="checkbox"
                  checked={form.is_synthetic}
                  onChange={(e) => setForm((f) => ({ ...f, is_synthetic: e.target.checked }))}
                />
                <span className="text-sm">Mark as synthetic/demonstration data</span>
              </label>

              <button type="submit" className="btn btn-primary" disabled={!form.zone || submitting} aria-busy={submitting}>
                {submitting ? <><div className="spinner" style={{ width: 14, height: 14 }} />Saving…</> : "Save Outcome"}
              </button>
            </div>
          </form>
        </div>

        {/* Evaluation metrics */}
        <div className="card">
          <h2 style={{ marginBottom: "0.75rem" }}>Model Evaluation Metrics</h2>
          {latestEval ? (
            <div>
              <div className="grid-2" style={{ gap: "0.5rem", marginBottom: "0.75rem" }}>
                {[
                  ["Precision", latestEval.precision],
                  ["Recall", latestEval.recall],
                  ["F1 Score", latestEval.f1_score],
                  ["Accuracy", latestEval.accuracy],
                ].map(([label, val]) => (
                  <div key={label} className="stat-card">
                    <div className="stat-label">{label}</div>
                    <div className="stat-value" style={{ fontSize: "1.5rem" }}>
                      {val !== null ? (val * 100).toFixed(1) + "%" : "—"}
                    </div>
                  </div>
                ))}
              </div>
              <div className="text-sm text-muted">
                <strong>n = {latestEval.n_observations}</strong> verified observations ·
                TP: {latestEval.true_positives} FP: {latestEval.false_positives} FN: {latestEval.false_negatives} TN: {latestEval.true_negatives}
              </div>
              <div className="alert alert-warning" style={{ marginTop: "0.5rem", fontSize: "0.8rem" }}>
                {latestEval.limitations_notes}
              </div>
              <div className="text-sm text-muted">
                Model: {latestEval.model_version} · Threshold: {latestEval.classification_threshold}<br />
                Evaluated: {new Date(latestEval.evaluated_at).toLocaleString()}
              </div>
            </div>
          ) : (
            <div>
              <p className="text-muted">
                No evaluation computed yet. At least {10} verified outcomes are required.
              </p>
            </div>
          )}
          <button
            className="btn btn-secondary"
            onClick={handleComputeMetrics}
            disabled={computing}
            aria-busy={computing}
            style={{ marginTop: "0.75rem" }}
          >
            {computing ? <><div className="spinner" style={{ width: 14, height: 14 }} />Computing…</> : "Compute Metrics"}
          </button>
        </div>
      </div>

      {/* Outcome history */}
      <h2 style={{ marginBottom: "0.75rem" }}>Outcome History</h2>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div className="loading"><div className="spinner" /><span>Loading…</span></div>
        ) : outcomes.length === 0 ? (
          <p className="text-muted" style={{ padding: "2rem", textAlign: "center" }}>
            No outcomes recorded yet. Use the form above to record your first observation.
          </p>
        ) : (
          <table aria-label="Waterlogging outcome history">
            <thead>
              <tr>
                <th>Zone</th>
                <th>Outcome</th>
                <th>Severity</th>
                <th>Source</th>
                <th>Window Start</th>
                <th>Synthetic</th>
              </tr>
            </thead>
            <tbody>
              {outcomes.map((o) => (
                <tr key={o.id}>
                  <td>
                    <span style={{ fontWeight: 600 }}>{o.zone_code}</span>
                  </td>
                  <td>
                    <span className={`badge ${o.outcome === "OCCURRED" ? "badge-high" : o.outcome === "NOT_OCCURRED" ? "badge-low" : "badge-unknown"}`}>
                      {o.outcome_display}
                    </span>
                  </td>
                  <td>{o.severity || "—"}</td>
                  <td className="text-sm text-muted">{o.report_source}</td>
                  <td className="mono text-sm">{new Date(o.observation_window_start).toLocaleString()}</td>
                  <td>{o.is_synthetic ? <span className="badge badge-moderate">Synthetic</span> : <span className="badge badge-low">Real</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
