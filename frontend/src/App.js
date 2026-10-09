import React from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import RiskMap from "./pages/RiskMap";
import ZoneDetail from "./pages/ZoneDetail";
import InterventionQueue from "./pages/InterventionQueue";
import OutcomeTracking from "./pages/OutcomeTracking";
import Transparency from "./pages/Transparency";
import "./App.css";

function NavBar() {
  return (
    <nav className="navbar" role="navigation" aria-label="Main navigation">
      <div className="navbar-brand">
        <span className="navbar-logo" aria-hidden="true">🌧</span>
        <span className="navbar-title">DrainSense AI</span>
        <span className="navbar-subtitle">Coimbatore</span>
      </div>
      <ul className="navbar-links" role="list">
        <li><NavLink to="/" end>Dashboard</NavLink></li>
        <li><NavLink to="/map">Risk Map</NavLink></li>
        <li><NavLink to="/interventions">Interventions</NavLink></li>
        <li><NavLink to="/outcomes">Outcomes</NavLink></li>
        <li><NavLink to="/transparency">Data & Model</NavLink></li>
      </ul>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <NavBar />
        <main className="app-main" role="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/map" element={<RiskMap />} />
            <Route path="/zones/:id" element={<ZoneDetail />} />
            <Route path="/interventions" element={<InterventionQueue />} />
            <Route path="/outcomes" element={<OutcomeTracking />} />
            <Route path="/transparency" element={<Transparency />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
