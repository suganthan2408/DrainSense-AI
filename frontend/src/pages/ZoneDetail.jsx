import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchZone, fetchRainfall, fetchForecasts, fetchAssessments, assessZone, runAgentExplain, fetchInterventions } from "../api";
import RiskBadge from "../components/RiskBadge";
import SyntheticDataBanner from "../components/SyntheticDataBanner";

export default function ZoneDetail() {
  const { id } = useParams();
  const [zone, setZone] = useState(null);
  const [rainfall, setRainfall] = useState([]);
  const [forecasts, setForecasts] = useState([]);
  const [assessments, setAssessments] = useState([]);
  const [agentResult, setAgentResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [assessing, setAssessing] = useState(false);
  const [agentRunning, setAgentRunning] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [z, r, f, a] = await Promise.all([
        fetchZone(id),
        fetchRainfall(id),
        fetchForecasts(id),
        fetchAssessments(id),
      ]);
      setZone(z);
      setRainfall((r.results || r).slice(0, 5));
      setForecasts((f.results || f).slice(0, 12));
      setAssessments((a.results || a).slice(0, 5));
    } catch (e) {
      setError("Failed to load zone data: " + e.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleAssess = async () => {
    setAssessing(true);
    setError(null);
    try {
      await assessZone(id);
      await load();
    } catch (e) {
      setError("Assessment failed: " + (e.response?.data?.error || e.message));
    } finally {
      setAssessing(false);
    }
  };

  const handleAgentExplain = async () => {
    const latest = assessments[0];
    if (!latest) { setError("Run an assessment first."); return; }
    // Find intervention linked to this zone
    setAgentRunning(true);
    setError(null);
    try {
      // Call agent via intervention endpoint if available
      const invData = await fetchInterventions({ zone: id });
      const invList = invData.results || invData;
      if (invList.length === 0) { setError("No interventions found for this zone. Run an assessment first."); setAgentRunning(false); return; }
      const result = await runAgentExplain(invList[0].id);
      setAgentResult(result);
    } catch (e) {
      setError("Agent failed: " + (e.response?.data?.error || e.message));
    } finally {
      setAgentRunning(false);
    }
  };

  if (loading) return <div className="loading"><div className="spinner" /><span>Loading zone…</span></div>;
  if (!zone) return <div className="alert alert-error">{error || "Zone not found."}</div>;

  const latest = assessments[0];

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/map" className="text-muted text-sm" style={{ display: "block", marginBottom: 4 }}>← Back to map</Link>
          <h1 className="page-title">{zone.name}</h1>
          <p className="page-subtitle mono">{zone.code} · {zone.latitude.toFixed(4)}°N, {zone.longitude.toFixed(4)}°E</p>
        </div>
        {latest && <RiskBadge category={latest.risk_category} />}
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      <SyntheticDataBanner />

      <div className="grid-2" style={{ gap: "1rem", marginBottom: "1rem" }}>
        {/* Zone attributes */}
        <div className="card">
          <h2 style={{ marginBottom: "0.75rem" }}>Zone Attributes</h2>
          <table aria-label="Zone physical attributes">
            <tbody>
              <tr><td className="text-muted text-sm">Elevation (avg)</td><td>{zone.avg_elevation_m ? `${zone.avg_elevation_m} m` : "Unknown"}</td></tr>
              <tr><td className="text-muted text-sm">Elevation (min)</td><td>{zone.min_elevation_m ? `${zone.min_elevation_m} m` : "Unknown"}</td></tr>
              <tr><td className="text-muted text-sm">Drain density</td><td>{zone.drainage_density ? `${zone.drainage_density} km/km²` : "Unknown"}</td></tr>
              <tr><td className="text-muted text-sm">Impervious</td><td>{zone.imperviousness_pct ? `${zone.imperviousness_pct}%` : "Unknown"}</td></tr>
              <tr><td className="text-muted text-sm">Area</td><td>{zone.area_km2 ? `${zone.area_km2} km²` : "Unknown"}</td></tr>
              <tr><td className="text-muted text-sm">Pop. density</td><td>{zone.population_density ? `${zone.population_density} /km²` : "Unknown"}</td></tr>
              <tr><td className="text-muted text-sm">Flood history</td><td>{zone.historical_flood_count} events recorded</td></tr>
              {zone.last_flood_date && <tr><td className="text-muted text-sm">Last flood</td><td>{zone.last_flood_date}</td></tr>}
              <tr><td className="text-muted text-sm">Data source</td><td className="text-sm">{zone.data_source}</td></tr>
            </tbody>
          </table>
          {zone.is_synthetic && (
            <p className="text-sm" style={{ color: "var(--risk-moderate)", marginTop: "0.5rem", marginBottom: 0 }}>
              ⚠ Zone attributes are synthetic demonstration data
            </p>
          )}
        </div>

        {/* Latest assessment */}
        <div className="card">
          <h2 style={{ marginBottom: "0.75rem" }}>Latest Risk Assessment</h2>
          {latest ? (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <div>
                  <div style={{ fontSize: "2rem", fontWeight: 700 }}>{latest.risk_score}</div>
                  <div className="text-muted text-sm">Heuristic score (0–100, not a probability)</div>
                </div>
                <RiskBadge category={latest.risk_category} />
              </div>
              <div className="text-sm text-muted" style={{ marginBottom: "0.5rem" }}>
                Method: {latest.score_method_display} · Version: {latest.model_version}<br />
                Confidence: <strong>{latest.confidence_level}</strong> · {new Date(latest.assessed_at).toLocaleString()}
              </div>

              {latest.data_warnings?.length > 0 && (
                <div>
                  {latest.data_warnings.map((w, i) => (
                    <div key={i} className="alert alert-warning" style={{ fontSize: "0.8rem" }}>{w}</div>
                  ))}
                </div>
              )}

              {/* Contributing factors */}
              {latest.contributing_factors && (
                <div>
                  <h3 style={{ marginBottom: "0.5rem" }}>Contributing Factors</h3>
                  {Object.entries(latest.contributing_factors).map(([key, val]) => (
                    <div key={key} style={{ marginBottom: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span className="text-sm">{key.replace(/_/g, " ")}</span>
                        <span className="text-sm mono">{val.component_contribution?.toFixed(1)} pts</span>
                      </div>
                      <div style={{ height: 5, background: "var(--color-border)", borderRadius: 3, marginTop: 3 }}>
                        <div style={{
                          height: "100%",
                          borderRadius: 3,
                          width: `${(val.value || 0)}%`,
                          background: "var(--color-accent)",
                          opacity: 0.7,
                        }} aria-hidden="true" />
                      </div>
                      <div className="text-sm text-muted">{val.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-muted">No assessment yet. Click "Run Assessment" to score this zone.</p>
          )}

          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
            <button className="btn btn-primary" onClick={handleAssess} disabled={assessing} aria-busy={assessing}>
              {assessing ? <><div className="spinner" style={{ width: 14, height: 14 }} />Assessing…</> : "▶ Run Assessment"}
            </button>
            {latest && (
              <button className="btn btn-secondary" onClick={handleAgentExplain} disabled={agentRunning} aria-busy={agentRunning}>
                {agentRunning ? <><div className="spinner" style={{ width: 14, height: 14 }} />Running agent…</> : "🤖 AWS Agent Explain"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Agent result */}
      {agentResult && (
        <div className="card" style={{ marginBottom: "1rem", borderLeft: "3px solid var(--color-accent)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <h2 style={{ margin: 0 }}>🤖 AWS Strands Agent Explanation</h2>
            <span className={`badge ${agentResult.agent_available ? "badge-low" : "badge-moderate"}`}>
              {agentResult.agent_available ? "Bedrock" : "Fallback"}
            </span>
          </div>
          <p style={{ fontSize: "0.875rem", marginBottom: "0.75rem" }}>{agentResult.risk_summary}</p>
          {agentResult.data_limitations?.length > 0 && (
            <div>
              {agentResult.data_limitations.map((l, i) => (
                <div key={i} className="alert alert-warning" style={{ fontSize: "0.8rem" }}>{l}</div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <div><span className="text-muted text-sm">Recommended Action: </span><strong>{agentResult.recommended_action}</strong></div>
            <div><span className="text-muted text-sm">Urgency: </span><strong>{agentResult.urgency}</strong></div>
            <div><span className="text-muted text-sm">Human verification: </span><strong>{agentResult.human_verification_required ? "Required" : "Not required"}</strong></div>
          </div>
          {agentResult.fallback_reason && (
            <p className="text-sm text-muted" style={{ marginTop: "0.5rem", marginBottom: 0 }}>
              Note: {agentResult.fallback_reason}
            </p>
          )}
        </div>
      )}

      <div className="grid-2" style={{ gap: "1rem" }}>
        {/* Rainfall observations */}
        <div className="card">
          <h2 style={{ marginBottom: "0.75rem" }}>Rainfall Observations</h2>
          {rainfall.length === 0 ? (
            <p className="text-muted">No rainfall observations loaded. Run <code>seed_observations</code>.</p>
          ) : (
            <table aria-label="Rainfall observations">
              <thead><tr><th>Time</th><th>1h (mm)</th><th>24h (mm)</th><th>Source</th></tr></thead>
              <tbody>
                {rainfall.map((r) => (
                  <tr key={r.id}>
                    <td className="mono text-sm">{new Date(r.observed_at).toLocaleString()}</td>
                    <td>{r.rainfall_1h_mm ?? r.rainfall_mm}</td>
                    <td>{r.rainfall_24h_mm ?? "—"}</td>
                    <td className="text-sm text-muted">{r.is_estimated ? "Estimated" : "Measured"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Forecasts */}
        <div className="card">
          <h2 style={{ marginBottom: "0.75rem" }}>Rainfall Forecast (Open-Meteo)</h2>
          {forecasts.length === 0 ? (
            <p className="text-muted">No forecast data. Forecasts are fetched live from Open-Meteo.</p>
          ) : (
            <table aria-label="Rainfall forecast">
              <thead><tr><th>Time</th><th>Rain (mm)</th><th>Prob %</th><th>Horizon</th></tr></thead>
              <tbody>
                {forecasts.map((f) => (
                  <tr key={f.id}>
                    <td className="mono text-sm">{new Date(f.forecast_for).toLocaleString()}</td>
                    <td>{f.rainfall_mm?.toFixed(1)}</td>
                    <td>{f.precipitation_probability_pct ?? "—"}</td>
                    <td className="text-muted text-sm">+{f.forecast_horizon_hours?.toFixed(0)}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
