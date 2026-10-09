import React from "react";

export default function SyntheticDataBanner() {
  return (
    <div className="alert alert-warning" role="note" aria-label="Data notice">
      ⚠ Some or all data displayed is <strong>synthetic demonstration data</strong>, not official
      measurements. Risk scores are heuristic estimates (0–100), not probability percentages.
      Always verify with field inspection before taking consequential action.
    </div>
  );
}
