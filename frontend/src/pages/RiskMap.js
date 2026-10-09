import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from "react-leaflet";
import { fetchZones, assessZone } from "../api";
import RiskBadge from "../components/RiskBadge";
import SyntheticDataBanner from "../components/SyntheticDataBanner";

const RISK_COLORS = {
  LOW: "#22c55e",
  MODERATE: "#eab308",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
  UNKNOWN: "#64748b",
};

function FitBounds({ zones }) {
  const map = useMap();
  useEffect(() => {
    if (zones.length > 0) {
      const lats = zones.map((z) => z.latitude);
      const lngs = zones.map((z) => z.longitude);
      map.fitBounds([
        [Math.min(...lats) - 0.02, Math.min(...lngs) - 0.02],
        [Math.max(...lats) + 0.02, Math.max(...lngs) + 0.02],
      ]);
    }
  }, [zones, map]);
  return null;
}

export default function RiskMap() {
  const [zones, setZones] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [assessing, setAssessing] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    fetchZones()
      .then((data) => setZones(data.results || data))
      .catch(() => setError("Failed to load zones. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  const handleAssess = async (zone) => {
    setAssessing(true);
    try {
      await assessZone(zone.id);
      const fresh = await fetchZones();
      const freshZones = fresh.results || fresh;
      setZones(freshZones);
      setSelected(freshZones.find((z) => z.id === zone.id) || zone);
    } catch (e) {
      setError("Assessment failed: " + (e.response?.data?.error || e.message));
    } finally {
      setAssessing(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Risk Map</h1>
          <p className="page-subtitle">Select a zone to view risk details and run an assessment</p>
        </div>
      </div>

      <SyntheticDataBanner />

      {error && <div className="alert alert-error">{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "1rem", height: "calc(100vh - 220px)", minHeight: "480px" }}>
        {/* Map */}
        <div style={{ borderRadius: "var(--radius)", overflow: "hidden", border: "1px solid var(--color-border)" }}>
          {loading ? (
            <div className="loading"><div className="spinner" /><span>Loading map…</span></div>
          ) : (
            <MapContainer
              center={[11.0, 77.0]}
              zoom={12}
              style={{ height: "100%", width: "100%" }}
              aria-label="Coimbatore drainage zone risk map"
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              <FitBounds zones={zones} />
              {zones.map((z) => {
                const cat = z.latest_risk_category || "UNKNOWN";
                const color = RISK_COLORS[cat] || RISK_COLORS.UNKNOWN;
                const radius = cat === "CRITICAL" ? 18 : cat === "HIGH" ? 15 : cat === "MODERATE" ? 12 : 9;
                return (
                  <CircleMarker
                    key={z.id}
                    center={[z.latitude, z.longitude]}
                    radius={radius}
                    pathOptions={{
                      color: selected?.id === z.id ? "#ffffff" : color,
                      fillColor: color,
                      fillOpacity: 0.75,
                      weight: selected?.id === z.id ? 3 : 1.5,
                    }}
                    eventHandlers={{ click: () => setSelected(z) }}
                    aria-label={`${z.name}: ${cat} risk`}
                  >
                    <Tooltip>
                      <strong>{z.name}</strong><br />
                      {z.code} · {cat} risk · Score: {z.latest_risk_score ?? "not assessed"}
                    </Tooltip>
                  </CircleMarker>
                );
              })}
            </MapContainer>
          )}
        </div>

        {/* Legend + zone panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", overflowY: "auto" }}>
          {/* Legend */}
          <div className="card">
            <h3 style={{ marginBottom: "0.5rem" }}>Risk Legend</h3>
            <p className="text-sm text-muted" style={{ marginBottom: "0.5rem" }}>
              Circle size and colour indicate risk category. Score is 0–100 (heuristic, not probability).
            </p>
            {Object.entries(RISK_COLORS).filter(([k]) => k !== "UNKNOWN").map(([cat, color]) => (
              <div key={cat} style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <div style={{ width: 14, height: 14, borderRadius: "50%", background: color, flexShrink: 0 }} aria-hidden="true" />
                <span style={{ fontSize: "0.82rem" }}>{cat}</span>
              </div>
            ))}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{ width: 14, height: 14, borderRadius: "50%", background: RISK_COLORS.UNKNOWN, flexShrink: 0 }} aria-hidden="true" />
              <span style={{ fontSize: "0.82rem" }}>UNKNOWN / Not assessed</span>
            </div>
          </div>

          {/* Selected zone panel */}
          {selected ? (
            <div className="card" style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                <div>
                  <h3 style={{ marginBottom: 2 }}>{selected.name}</h3>
                  <span className="text-muted text-sm mono">{selected.code}</span>
                </div>
                <RiskBadge category={selected.latest_risk_category} />
              </div>

              {selected.latest_risk_score !== null ? (
                <div style={{ marginBottom: "0.75rem" }}>
                  <div className="text-sm text-muted" style={{ marginBottom: 4 }}>Risk Score</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{
                      height: 8, flex: 1, borderRadius: 4,
                      background: "var(--color-border)",
                    }}>
                      <div style={{
                        height: "100%",
                        borderRadius: 4,
                        width: `${selected.latest_risk_score}%`,
                        background: RISK_COLORS[selected.latest_risk_category] || RISK_COLORS.UNKNOWN,
                        transition: "width 0.4s",
                      }} aria-hidden="true" />
                    </div>
                    <span style={{ fontWeight: 700, fontSize: "1rem" }}>
                      {selected.latest_risk_score}
                    </span>
                  </div>
                  {selected.is_synthetic && (
                    <p className="text-sm" style={{ color: "var(--risk-moderate)", marginTop: 4 }}>
                      ⚠ Synthetic zone data
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-muted text-sm">Not yet assessed. Run assessment below.</p>
              )}

              <table style={{ marginBottom: "0.75rem" }} aria-label="Zone attributes">
                <tbody>
                  {selected.avg_elevation_m && (
                    <tr><td className="text-muted text-sm" style={{ padding: "3px 8px 3px 0" }}>Elevation</td><td>{selected.avg_elevation_m} m</td></tr>
                  )}
                  {selected.drainage_density && (
                    <tr><td className="text-muted text-sm" style={{ padding: "3px 8px 3px 0" }}>Drain density</td><td>{selected.drainage_density} km/km²</td></tr>
                  )}
                  {selected.imperviousness_pct && (
                    <tr><td className="text-muted text-sm" style={{ padding: "3px 8px 3px 0" }}>Impervious</td><td>{selected.imperviousness_pct}%</td></tr>
                  )}
                  <tr><td className="text-muted text-sm" style={{ padding: "3px 8px 3px 0" }}>Flood history</td><td>{selected.historical_flood_count} events</td></tr>
                </tbody>
              </table>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <button
                  className="btn btn-primary"
                  onClick={() => handleAssess(selected)}
                  disabled={assessing}
                  aria-busy={assessing}
                >
                  {assessing ? <><div className="spinner" style={{ width: 14, height: 14 }} />Assessing…</> : "▶ Run Risk Assessment"}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => navigate(`/zones/${selected.id}`)}
                >
                  View Full Details
                </button>
              </div>

              {selected.latest_assessed_at && (
                <p className="text-sm text-muted" style={{ marginTop: "0.5rem", marginBottom: 0 }}>
                  Last assessed: {new Date(selected.latest_assessed_at).toLocaleString()}
                </p>
              )}
            </div>
          ) : (
            <div className="card" style={{ textAlign: "center" }}>
              <p className="text-muted" style={{ margin: "1rem 0" }}>
                Click a zone on the map to view details and run a risk assessment.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
