import React, {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";
import { fetchDistricts, fetchStates, fetchZones } from "./api";

const LocationContext = createContext(null);

function listFrom(response) {
  return response?.results || response || [];
}

export function LocationProvider({ children }) {
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [zones, setZones] = useState([]);
  const [stateCode, setStateCode] = useState("");
  const [districtCode, setDistrictCode] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [loadingStates, setLoadingStates] = useState(true);
  const [loadingDistricts, setLoadingDistricts] = useState(false);
  const [loadingZones, setLoadingZones] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchStates()
      .then((response) => setStates(listFrom(response)))
      .catch(() => setError("Unable to load state and union territory reference data."))
      .finally(() => setLoadingStates(false));
  }, []);

  useEffect(() => {
    setDistrictCode("");
    setZoneId("");
    setZones([]);
    setDistricts([]);
    setLoadingDistricts(false);
    if (!stateCode) {
      return undefined;
    }

    let active = true;
    setLoadingDistricts(true);
    fetchDistricts(stateCode)
      .then((response) => {
        if (active) setDistricts(listFrom(response));
      })
      .catch(() => {
        if (active) setError("Unable to load districts for the selected state.");
      })
      .finally(() => {
        if (active) setLoadingDistricts(false);
      });
    return () => { active = false; };
  }, [stateCode]);

  useEffect(() => {
    setZoneId("");
    setLoadingZones(false);
    if (!districtCode) {
      setZones([]);
      return undefined;
    }

    let active = true;
    setLoadingZones(true);
    fetchZones({ state: stateCode, district: districtCode })
      .then((response) => {
        if (active) setZones(listFrom(response));
      })
      .catch(() => {
        if (active) setError("Unable to load monitoring zones for the selected district.");
      })
      .finally(() => {
        if (active) setLoadingZones(false);
      });
    return () => { active = false; };
  }, [stateCode, districtCode]);

  const changeState = useCallback((value) => {
    setError("");
    setStateCode(value);
  }, []);
  const changeDistrict = useCallback((value) => {
    setError("");
    setDistrictCode(value);
  }, []);
  const changeZone = useCallback((value) => {
    setError("");
    setZoneId(value);
  }, []);

  const locationParams = useMemo(() => {
    const params = {};
    if (stateCode) params.state = stateCode;
    if (districtCode) params.district = districtCode;
    if (zoneId) params.zone = zoneId;
    return params;
  }, [stateCode, districtCode, zoneId]);

  const selectedState = states.find((item) => item.code === stateCode);
  const selectedDistrict = districts.find((item) => item.code === districtCode);
  const selectedZone = zones.find((item) => String(item.id) === zoneId);
  const scopeLabel = selectedZone
    ? `${selectedZone.name} · ${selectedDistrict?.name || ""}, ${selectedState?.name || ""}`
    : selectedDistrict
      ? `${selectedDistrict.name}, ${selectedState?.name || ""}`
      : selectedState?.name || "India — national overview";

  const value = useMemo(() => ({
    states,
    districts,
    zones,
    stateCode,
    districtCode,
    zoneId,
    loadingStates,
    loadingDistricts,
    loadingZones,
    changeState,
    changeDistrict,
    changeZone,
    locationParams,
    scopeLabel,
  }), [
    states, districts, zones, stateCode, districtCode, zoneId,
    loadingStates, loadingDistricts, loadingZones,
    changeState, changeDistrict, changeZone, locationParams, scopeLabel,
  ]);

  return (
    <LocationContext.Provider value={value}>
      {error && <div className="location-global-error" role="alert">{error}</div>}
      {children}
    </LocationContext.Provider>
  );
}

export function useLocationScope() {
  const context = useContext(LocationContext);
  if (!context) throw new Error("useLocationScope must be used inside LocationProvider.");
  return context;
}

export function LocationSelector() {
  const {
    states, districts, zones, stateCode, districtCode, zoneId,
    loadingStates, loadingDistricts, loadingZones,
    changeState, changeDistrict, changeZone,
  } = useLocationScope();

  return (
    <div className="location-controls" aria-label="Geographic filters">
      <label>
        <span>State / UT</span>
        <select value={stateCode} disabled={loadingStates} onChange={(event) => changeState(event.target.value)}>
          <option value="">{loadingStates ? "Loading states…" : "India — national overview"}</option>
          {states.map((state) => (
            <option key={state.code} value={state.code}>
              {state.name}{state.is_verified ? "" : " (reference pending verification)"}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>District</span>
        <select
          value={districtCode}
          disabled={!stateCode || loadingDistricts}
          onChange={(event) => changeDistrict(event.target.value)}
        >
          <option value="">
            {!stateCode ? "Select a state first" : loadingDistricts ? "Loading districts…" : districts.length ? "All available districts" : "No districts imported"}
          </option>
          {districts.map((district) => (
            <option key={district.code} value={district.code}>
              {district.name}{district.is_verified ? "" : " (reference pending verification)"}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Monitoring zone</span>
        <select
          value={zoneId}
          disabled={!districtCode || loadingZones}
          onChange={(event) => changeZone(event.target.value)}
        >
          <option value="">
            {!districtCode ? "Select a district first" : loadingZones ? "Loading zones…" : zones.length ? "All zones in district" : "No zones available"}
          </option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>{zone.name} ({zone.code})</option>
          ))}
        </select>
      </label>
    </div>
  );
}
