import React from "react";

const CATEGORY_CLASS = {
  LOW: "badge-low",
  MODERATE: "badge-moderate",
  HIGH: "badge-high",
  CRITICAL: "badge-critical",
  UNKNOWN: "badge-unknown",
};

export default function RiskBadge({ category }) {
  const cls = CATEGORY_CLASS[category] || "badge-unknown";
  return (
    <span className={`badge ${cls}`} role="status" aria-label={`Risk level: ${category || "Unknown"}`}>
      {category || "UNKNOWN"}
    </span>
  );
}
