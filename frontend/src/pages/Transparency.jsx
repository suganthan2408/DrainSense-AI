import React, { useEffect, useState } from "react";
import { fetchDataSources, fetchAgentStatus } from "../api";
import { useLocationScope } from "../LocationContext";

export default function Transparency() {
  const [sources, setSources] = useState([]);
  const [agentStatus, setAgentStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { scopeLabel } = useLocationScope();

  useEffect(() => {
    Promise.all([fetchDataSources(), fetchAgentStatus()])
      .then(([s, a]) => {
        setSources(s.results || s);
        setAgentStatus(a);
      })
      .catch(() => setError("Could not load transparency data. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Data & Model Transparency</h1>
          <p className="page-subtitle">Sources and model documentation · Current location scope: {scopeLabel}</p>
        </div>
      </div>

      <div className="alert alert-info" style={{ marginBottom: "1.5rem" }}>
        DrainSense AI is a decision-support tool, not an authoritative flood prediction system.
        Always verify with field inspection before taking consequential action.
      </div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}

      <div className="grid-2" style={{ gap: "1rem", marginBottom: "1rem" }}>
        {/* Model */}
        <div className="card">
          <h2 style={{ marginBottom: "0.75rem" }}>Risk Model</h2>
          <table aria-label="Model information">
            <tbody>
              <tr><td className="text-muted text-sm">Version</td><td className="mono">heuristic-v1</td></tr>
              <tr><td className="text-muted text-sm">Method</td><td>Heuristic rule-based score</td></tr>
              <tr><td className="text-muted text-sm">Output</td><td>Score 0–100 + category (LOW/MODERATE/HIGH/CRITICAL)</td></tr>
              <tr><td className="text-muted text-sm">NOT</td><td>A calibrated probability of flooding</td></tr>
              <tr><td className="text-muted text-sm">Validated</td><td>Not yet — insufficient labeled outcome data</td></tr>
            </tbody>
          </table>
          <div className="alert alert-warning" style={{ marginTop: "0.75rem" }}>
            <strong>Limitations:</strong> The heuristic scorer uses fixed weights derived from rainfall
            intensity classification (IMD guidelines), elevation, drainage density, imperviousness,
            and historical flood counts. Weights were not tuned on a validated dataset. The score is
            designed to rank zones relative to each other, not to estimate absolute flood probability.
          </div>
          <h3 style={{ margin: "0.75rem 0 0.5rem" }}>Scoring Weights</h3>
          {[
            ["Rainfall intensity (current)", 35],
            ["Forecast rainfall (6h)", 20],
            ["Elevation risk", 20],
            ["Drainage infrastructure", 10],
            ["Impervious surface", 8],
            ["Historical flood frequency", 7],
          ].map(([label, pct]) => (
            <div key={label} style={{ marginBottom: 6 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span className="text-sm">{label}</span>
                <span className="text-sm mono">{pct}%</span>
              </div>
              <div style={{ height: 5, background: "var(--color-border)", borderRadius: 3 }}>
                <div style={{ height: "100%", borderRadius: 3, width: `${pct}%`, background: "var(--color-accent)" }} aria-hidden="true" />
              </div>
            </div>
          ))}
        </div>

        {/* AWS Agent */}
        <div className="card">
          <h2 style={{ marginBottom: "0.75rem" }}>Strands Agent</h2>
          {loading ? (
            <div className="loading"><div className="spinner" /></div>
          ) : agentStatus ? (
            <div>
              <table aria-label="Agent status">
                <tbody>
                  <tr>
                    <td className="text-muted text-sm">SDK</td>
                    <td>
                      <span className={`badge ${agentStatus.strands_sdk_available ? "badge-low" : "badge-high"}`}>
                        {agentStatus.strands_sdk_available ? "Installed" : "Not installed"}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td className="text-muted text-sm">AWS credentials</td>
                    <td>
                      <span className={`badge ${agentStatus.aws_credentials_configured ? "badge-low" : "badge-moderate"}`}>
                        {agentStatus.aws_credentials_configured ? "Configured" : "Not configured"}
                      </span>
                    </td>
                  </tr>
                  <tr><td className="text-muted text-sm">Selected provider</td><td className="mono">{agentStatus.agent_model_provider}</td></tr>
                  <tr><td className="text-muted text-sm">Configured model</td><td className="mono">{agentStatus.agent_model_id || "—"}</td></tr>
                  <tr>
                    <td className="text-muted text-sm">Mode</td>
                    <td>
                      <span className={`badge ${agentStatus.agent_mode === "fallback" ? "badge-moderate" : "badge-low"}`}>
                        {agentStatus.agent_mode === "aws_bedrock" ? "AWS Bedrock selected" : agentStatus.agent_mode === "ollama_local" ? "Local Ollama selected" : "Fallback (deterministic)"}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div className="alert alert-info" style={{ marginTop: "0.75rem" }}>
                The agent uses the <strong>Strands Agents SDK</strong>. Configure local Ollama or
                Amazon Bedrock as the model provider. Provider selection is not proof of a successful
                model call; each explanation indicates whether a model ran or deterministic fallback was returned.
                The agent explains existing risk assessments — it does not fabricate sensor readings
                or model metrics.
              </div>
              <div className="alert alert-warning">
                {agentStatus.agent_mode === "ollama_local"
                  ? "Ollama provider is selected, but the local server/model is not checked here. Use a successful Agent Explain response to verify execution."
                  : agentStatus.agent_mode === "aws_bedrock"
                    ? `Bedrock is selected in ${agentStatus.aws_region}; configuration does not confirm model access or execution.`
                    : "The configured provider is not ready; explanations use the deterministic fallback until its prerequisites are met."}
              </div>
              {agentStatus.agent_model_provider === "ollama" && !agentStatus.strands_ollama_provider_available && (
                <div className="alert alert-warning">
                  Install the Strands Ollama extra and run the configured local model server to enable Ollama calls.
                </div>
              )}
            </div>
          ) : (
            <p className="text-muted">Could not load agent status.</p>
          )}
        </div>
      </div>

      {/* Data sources */}
      <h2 style={{ marginBottom: "0.75rem" }}>Data Sources</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {(sources || []).map((s) => (
          <div key={s.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontWeight: 700 }}>{s.name}</div>
                {s.url && <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-sm">{s.url}</a>}
                {s.description && <p className="text-sm text-muted" style={{ margin: "4px 0 0" }}>{s.description}</p>}
                {s.license_info && <p className="text-sm text-muted" style={{ margin: "4px 0 0" }}>License: {s.license_info}</p>}
                {s.last_fetched_at && (
                  <p className="text-sm text-muted" style={{ margin: "4px 0 0" }}>
                    Last fetched: {new Date(s.last_fetched_at).toLocaleString()}
                  </p>
                )}
              </div>
              <div style={{ display: "flex", gap: "4px", flexShrink: 0 }}>
                <span className={`badge ${s.is_synthetic ? "badge-moderate" : "badge-low"}`}>
                  {s.is_synthetic ? "Synthetic" : "Real"}
                </span>
                <span className={`badge ${s.is_live ? "badge-low" : "badge-unknown"}`}>
                  {s.is_live ? "Live" : "Static"}
                </span>
              </div>
            </div>
          </div>
        ))}

        {/* Always-shown attribution */}
        <div className="card">
          <div style={{ fontWeight: 700 }}>SRTM 30m DEM (elevation reference)</div>
          <p className="text-sm text-muted" style={{ margin: "4px 0 0" }}>
            Shuttle Radar Topography Mission. NASA/JPL. Used to inform elevation estimates for synthetic zone data.
            <a href="https://www2.jpl.nasa.gov/srtm/" target="_blank" rel="noopener noreferrer"> NASA SRTM</a>
          </p>
          <span className="badge badge-moderate">Reference only</span>
        </div>
        <div className="card">
          <div style={{ fontWeight: 700 }}>IMD Rainfall Classification</div>
          <p className="text-sm text-muted" style={{ margin: "4px 0 0" }}>
            India Meteorological Department rainfall intensity thresholds used to calibrate the heuristic scorer.
            <a href="https://mausam.imd.gov.in/" target="_blank" rel="noopener noreferrer"> mausam.imd.gov.in</a>
          </p>
          <span className="badge badge-moderate">Reference only</span>
        </div>
      </div>

      {/* Third-party libraries */}
      <h2 style={{ margin: "1.5rem 0 0.75rem" }}>Third-Party Libraries</h2>
      <div className="card">
        <table aria-label="Third party library attributions">
          <thead><tr><th>Library</th><th>License</th><th>Use</th></tr></thead>
          <tbody>
            <tr><td>Django</td><td>BSD-3-Clause</td><td>Backend web framework</td></tr>
            <tr><td>Django REST Framework</td><td>BSD-3-Clause</td><td>API layer</td></tr>
            <tr><td>scikit-learn</td><td>BSD-3-Clause</td><td>ML evaluation utilities</td></tr>
            <tr><td>AWS Strands Agents SDK</td><td>Apache-2.0</td><td>AI agent integration</td></tr>
            <tr><td>boto3</td><td>Apache-2.0</td><td>AWS SDK for Python</td></tr>
            <tr><td>React</td><td>MIT</td><td>Frontend framework</td></tr>
            <tr><td>Leaflet / react-leaflet</td><td>BSD-2-Clause</td><td>Interactive maps</td></tr>
            <tr><td>OpenStreetMap</td><td>ODbL 1.0</td><td>Map tiles</td></tr>
            <tr><td>Open-Meteo</td><td>CC BY 4.0</td><td>Rainfall forecast API</td></tr>
            <tr><td>Recharts</td><td>MIT</td><td>Charts</td></tr>
            <tr><td>axios</td><td>MIT</td><td>HTTP client</td></tr>
          </tbody>
        </table>
      </div>

      {/* AI tools disclosure */}
      <h2 style={{ margin: "1.5rem 0 0.75rem" }}>AI Coding Tools Used</h2>
      <div className="card">
        <ul style={{ margin: 0, paddingLeft: 20 }} aria-label="AI coding tools used">
          <li><strong>GitHub Copilot</strong> — assisted with repository inspection, implementation, and verification for this completion pass.</li>
          <li><strong>Antigravity (Google DeepMind)</strong> — prior codebase review and submission preparation, as reported by the project team.</li>
          <li>All code was reviewed and verified by the team before submission.</li>
        </ul>
      </div>
    </div>
  );
}
