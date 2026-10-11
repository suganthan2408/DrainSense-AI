import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from "react-leaflet";
import { fetchZones, assessZone } from "../api";
import RiskBadge from "../components/RiskBadge";
import SyntheticDataBanner from "../components/SyntheticDataBanner";
import { useLocationScope } from "../LocationContext";

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
    const mapped = zones.filter(
      (zone) => Number.isFinite(zone.latitude) && Number.isFinite(zone.longitude),
    );
    if (mapped.length > 0) {
      const lats = mapped.map((z) => z.latitude);
      const lngs = mapped.map((z) => z.longitude);
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
  const { locationParams, scopeLabel, zoneId } = useLocationScope();

  useEffect(() => {
    setLoading(true);
    fetchZones(locationParams)
      .then((data) => {
        const rows = data.results || data;
        setZones(rows);
        setSelected((current) => (
          rows.find((zone) => String(zone.id) === zoneId)
          || rows.find((zone) => zone.id === current?.id)
          || null
        ));
      })
      .catch(() => setError("Failed to load zones. Is the backend running?"))
      .finally(() => setLoading(false));
  }, [locationParams, zoneId]);

  const mappedZones = zones.filter(
    (zone) => Number.isFinite(zone.latitude) && Number.isFinite(zone.longitude),
  );

  const handleAssess = async (zone) => {
    setAssessing(true);
    setError(null);
    try {
      await assessZone(zone.id);
      const fresh = await fetchZones(locationParams);
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
          <p className="page-subtitle">Scope: {scopeLabel}. Select a mapped zone to inspect its heuristic assessment.</p>
        </div>
      </div>

      <SyntheticDataBanner />

      {error && <div className="alert alert-error">{error}</div>}

      <div className="risk-map-layout">
        {/* Map */}
        <div className="risk-map-container">
          {loading ? (
            <div className="loading"><div className="spinner" /><span>Loading map…</span></div>
          ) : mappedZones.length === 0 ? (
            <div className="map-empty-state" role="status">
              No zone coordinates are available for {scopeLabel}. No markers or district polygons are fabricated.
            </div>
          ) : (
            <MapContainer
              center={[mappedZones[0].latitude, mappedZones[0].longitude]}
              zoom={12}
              style={{ height: "100%", width: "100%" }}
              aria-label={`${scopeLabel} drainage zone risk map`}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              <FitBounds zones={zones} />
              {mappedZones.map((z) => {
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
                      <br />{z.district_name || "District unavailable"}{z.state_name ? `, ${z.state_name}` : ""}
                      {z.is_synthetic && <><br />Synthetic demonstration location</>}
                      {z.latest_assessed_at && <><br />Assessed: {new Date(z.latest_assessed_at).toLocaleString()}</>}
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
              Existing demonstration-zone coordinates are synthetic; district boundaries are not loaded.
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
                  {selected.avg_elevation_m != null && (
                    <tr><td className="text-muted text-sm" style={{ padding: "3px 8px 3px 0" }}>Elevation</td><td>{selected.avg_elevation_m} m</td></tr>
                  )}
                  {selected.drainage_density != null && (
                    <tr><td className="text-muted text-sm" style={{ padding: "3px 8px 3px 0" }}>Drain density</td><td>{selected.drainage_density} km/km²</td></tr>
                  )}
                  {selected.imperviousness_pct != null && (
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
