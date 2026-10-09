/**
 * DrainSense AI — API client
 * All requests go to the Django backend at /api/v1/
 * React dev server proxies to http://localhost:8000 via package.json proxy setting.
 */

import axios from "axios";

const BASE = "/api/v1";

const client = axios.create({
  baseURL: BASE,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ---- Zones ----------------------------------------------------------------

export const fetchZones = () => client.get("/zones/zones/").then((r) => r.data);

export const fetchZone = (id) =>
  client.get(`/zones/zones/${id}/`).then((r) => r.data);

export const assessZone = (id) =>
  client.post(`/zones/zones/${id}/assess/`).then((r) => r.data);

// ---- Assessments ----------------------------------------------------------

export const fetchAssessments = (zoneId) => {
  const params = zoneId ? { zone: zoneId } : {};
  return client.get("/zones/assessments/", { params }).then((r) => r.data);
};

// ---- Observations ---------------------------------------------------------

export const fetchDataSources = () =>
  client.get("/observations/sources/").then((r) => r.data);

export const fetchRainfall = (zoneId) => {
  const params = zoneId ? { zone: zoneId } : {};
  return client.get("/observations/rainfall/", { params }).then((r) => r.data);
};

export const fetchForecasts = (zoneId) => {
  const params = zoneId ? { zone: zoneId } : {};
  return client.get("/observations/forecasts/", { params }).then((r) => r.data);
};

export const fetchForecastsLive = () =>
  client.post("/observations/forecasts/fetch/").then((r) => r.data);

// ---- Interventions --------------------------------------------------------

export const fetchInterventions = (params = {}) =>
  client.get("/interventions/", { params }).then((r) => r.data);

export const fetchIntervention = (id) =>
  client.get(`/interventions/${id}/`).then((r) => r.data);

export const updateInterventionStatus = (id, status, notes, assignedTo) =>
  client
    .patch(`/interventions/${id}/status/`, {
      status,
      notes: notes || "",
      assigned_to: assignedTo || "",
    })
    .then((r) => r.data);

export const explainIntervention = (id) =>
  client.post(`/interventions/${id}/explain/`).then((r) => r.data);

// ---- Outcomes -------------------------------------------------------------

export const fetchOutcomes = (zoneId) => {
  const params = zoneId ? { zone: zoneId } : {};
  return client.get("/outcomes/outcomes/", { params }).then((r) => r.data);
};

export const recordOutcome = (payload) =>
  client.post("/outcomes/outcomes/", payload).then((r) => r.data);

export const fetchEvaluations = () =>
  client.get("/outcomes/evaluations/").then((r) => r.data);

export const computeEvaluation = () =>
  client.post("/outcomes/evaluations/compute/").then((r) => r.data);

// ---- Agent ----------------------------------------------------------------

export const fetchAgentStatus = () =>
  client.get("/agent/status/").then((r) => r.data);

export const runAgentExplain = (interventionId) =>
  client.post(`/agent/explain/${interventionId}/`).then((r) => r.data);
