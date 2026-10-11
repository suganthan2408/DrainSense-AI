import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  fetchZones, fetchInterventions, fetchDataSources, fetchGeographicSummary,
} from "../api";
import RiskBadge from "../components/RiskBadge";
import SyntheticDataBanner from "../components/SyntheticDataBanner";
import { useLocationScope } from "../LocationContext";

function StatCard({ label, value, sub, color }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={color ? { color } : {}}>
        {value ?? "—"}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [zones, setZones] = useState([]);
  const [interventions, setInterventions] = useState([]);
  const [sources, setSources] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { locationParams, scopeLabel } = useLocationScope();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [zR, iR, sR, summaryR] = await Promise.all([
        fetchZones(locationParams),
        fetchInterventions({ ...locationParams, status: "PENDING" }),
        fetchDataSources(),
        fetchGeographicSummary(locationParams),
      ]);
      setZones(zR.results || zR);
      setInterventions(iR.results || iR);
      setSources(sR.results || sR);
      setSummary(summaryR);
    } catch (e) {
      setError("Failed to load dashboard data. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [locationParams]);

  useEffect(() => { load(); }, [load]);

  const criticalZones = summary?.risk_category_counts?.CRITICAL || 0;
  const highZones = summary?.risk_category_counts?.HIGH || 0;
  const topIntervention = interventions[0];
  const liveSources = sources.filter((s) => s.is_live);

  if (loading) return <div className="loading"><div className="spinner" /><span>Loading dashboard…</span></div>;
  if (error) return <div className="alert alert-error">{error}</div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🌧 DrainSense AI Dashboard</h1>
          <p className="page-subtitle">
            Geographic scope: {scopeLabel}. Coverage and risk indicators reflect records currently loaded.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={load} aria-label="Refresh dashboard">
          ↻ Refresh
        </button>
      </div>

      <SyntheticDataBanner />

      {/* Stats row */}
      <div className="grid-4" style={{ marginBottom: "1.5rem" }}>
        <StatCard
          label="State / district coverage"
          value={`${summary?.coverage?.states ?? "—"} / ${summary?.coverage?.districts ?? "—"}`}
          sub="States / districts in reference data"
        />
        <StatCard
          label="Zones with observations"
          value={`${summary?.coverage?.zones_with_observations ?? "—"} / ${summary?.coverage?.zones ?? "—"}`}
          sub={`${summary?.coverage?.zones_with_verified_observations ?? 0} with non-estimated, OK observations`}
        />
        <StatCard
          label="Critical / High"
          value={`${criticalZones} / ${highZones}`}
          sub="Assessed zones only; ranking scores, not probabilities"
          color={criticalZones > 0 ? "var(--risk-critical)" : "var(--risk-moderate)"}
        />
        <StatCard
          label="Pending Interventions"
          value={interventions.length}
          sub={`Pending in ${scopeLabel}`}
          color={interventions.length > 0 ? "var(--risk-high)" : "var(--risk-low)"}
        />
        <StatCard
          label="Sources marked live"
          value={liveSources.length}
          sub="System-wide source status; not a location-specific sensor count"
        />
      </div>
      {summary && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <strong>Coverage and freshness — {summary.scope}</strong>
          <p className="text-sm text-muted" style={{ marginBottom: 0 }}>
            {summary.coverage.synthetic_zones} synthetic zones; {summary.coverage.zones_with_forecasts} zones have forecast records.
            Latest observation: {summary.data_freshness.latest_observation_at
              ? new Date(summary.data_freshness.latest_observation_at).toLocaleString()
              : "none"}.
            {" "}Latest forecast issued: {summary.data_freshness.latest_forecast_issued_at
              ? new Date(summary.data_freshness.latest_forecast_issued_at).toLocaleString()
              : "none"}.
          </p>
          {zones.length === 0 && (
            <p className="text-sm" style={{ marginBottom: 0 }}>
              No monitoring zones are loaded for this scope; absence of records is not zero risk.
            </p>
          )}
        </div>
      )}

      <div className="grid-2" style={{ gap: "1.5rem" }}>
        {/* Zones table */}
        <div>
          <h2 style={{ marginBottom: "0.75rem" }}>Zone Risk Overview</h2>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table aria-label="Zone risk summary">
              <thead>
                <tr>
                  <th scope="col">Zone</th>
                  <th scope="col">Risk</th>
                  <th scope="col">Score</th>
                  <th scope="col">Action</th>
                </tr>
              </thead>
              <tbody>
                {zones.length === 0 && (
                  <tr><td colSpan={4} style={{ textAlign: "center", padding: "2rem", color: "var(--color-text-muted)" }}>
                    No zones found. Run <code>python manage.py seed_zones</code>.
                  </td></tr>
                )}
                {zones.map((z) => (
                  <tr key={z.id}>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>{z.name}</div>
                      <div className="text-muted text-sm mono">{z.code}</div>
                    </td>
                    <td><RiskBadge category={z.latest_risk_category} /></td>
                    <td>
                      {z.latest_risk_score !== null
                        ? <span className={`risk-${z.latest_risk_category}`}>{z.latest_risk_score}</span>
                        : <span className="text-muted">—</span>}
                    </td>
                    <td>
                      <Link to={`/zones/${z.id}`} className="btn btn-secondary" style={{ fontSize: "0.78rem", padding: "4px 10px" }}>
                        Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Interventions queue preview */}
        <div>
          <h2 style={{ marginBottom: "0.75rem" }}>Top Pending Interventions</h2>
          {topIntervention ? (
            <div>
              <div className="card" style={{ borderLeft: "3px solid var(--risk-critical)", marginBottom: "1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontWeight: 700, marginBottom: 4 }}>
                      #{topIntervention.priority_rank} — {topIntervention.zone_name}
                    </div>
                    <div className="text-muted text-sm mono">{topIntervention.zone_code}</div>
                  </div>
                  <RiskBadge category={topIntervention.urgency} />
                </div>
                <p style={{ margin: "0.75rem 0 0", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                  {topIntervention.reason?.slice(0, 180)}…
                </p>
              </div>
              <Link to="/interventions" className="btn btn-primary">
                View Full Priority Queue →
              </Link>
            </div>
          ) : (
            <div className="card">
              <p className="text-muted" style={{ margin: 0, textAlign: "center" }}>
                No pending interventions. Run an assessment from a zone to generate recommendations.
              </p>
            </div>
          )}

          {/* Data sources */}
          <h2 style={{ margin: "1.5rem 0 0.75rem" }}>Data Sources</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {sources.length === 0 && <p className="text-muted">No data sources recorded.</p>}
            {sources.map((s) => (
              <div key={s.id} className="card" style={{ padding: "0.6rem 1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 600, fontSize: "0.875rem" }}>{s.name}</span>
                  <span className={`badge ${s.is_synthetic ? "badge-moderate" : s.is_live ? "badge-low" : "badge-unknown"}`}>
                    {s.is_synthetic ? "Synthetic" : s.is_live ? "Live" : "Static"}
                  </span>
                </div>
                {s.last_fetched_at && (
                  <div className="text-muted text-sm">
                    Last fetched: {new Date(s.last_fetched_at).toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
