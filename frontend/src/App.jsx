import React from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import RiskMap from "./pages/RiskMap";
import ZoneDetail from "./pages/ZoneDetail";
import InterventionQueue from "./pages/InterventionQueue";
import OutcomeTracking from "./pages/OutcomeTracking";
import Transparency from "./pages/Transparency";
import { LocationProvider, LocationSelector, useLocationScope } from "./LocationContext";
import "./App.css";

function NavBar() {
  const { scopeLabel } = useLocationScope();

  return (
    <aside className="sidebar" role="navigation" aria-label="Main navigation">
      <div className="sidebar-brand">
        <div className="brand-icon" aria-hidden="true">💧</div>
        <div>
          <div className="brand-title">DrainSense AI</div>
          <div className="brand-subtitle">Predict flooding before it happens</div>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Sidebar navigation">
        <NavLink to="/" end className="nav-item">🏠 <span>Dashboard</span></NavLink>
        <NavLink to="/map" className="nav-item">🗺️ <span>Risk Map</span></NavLink>
        <NavLink to="/interventions" className="nav-item">📊 <span>Interventions</span></NavLink>
        <NavLink to="/outcomes" className="nav-item">📈 <span>Outcomes</span></NavLink>
        <NavLink to="/transparency" className="nav-item">🧠 <span>Data & Model</span></NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="scope-pill">{scopeLabel}</div>
      </div>
    </aside>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <LocationProvider>
        <div className="app-shell">
          <NavBar />
          <div className="main-panel">
            <header className="topbar">
              <div className="topbar-left">
                <span className="topbar-tag">Environmental Hacks 2026</span>
                <span className="topbar-divider">|</span>
                <span className="topbar-tag muted">Heat &amp; Water Track</span>
              </div>
              <div className="topbar-right">
                <div className="topbar-city">
                  <span>City</span>
                  <div className="city-select">Coimbatore</div>
                </div>
                <div className="topbar-user">Team Eco Warriors</div>
              </div>
            </header>

            <main className="app-main" role="main">
              <div className="geo-toolbar">
                <LocationSelector />
              </div>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/map" element={<RiskMap />} />
                <Route path="/zones/:id" element={<ZoneDetail />} />
                <Route path="/interventions" element={<InterventionQueue />} />
                <Route path="/outcomes" element={<OutcomeTracking />} />
                <Route path="/transparency" element={<Transparency />} />
                <Route path="*" element={<div className="card"><h1>Page not found</h1><NavLink to="/">Return to dashboard</NavLink></div>} />
              </Routes>
            </main>
          </div>
        </div>
      </LocationProvider>
    </BrowserRouter>
  );
}
