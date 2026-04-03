import React from "react";

interface RiskLevelBadgeProps {
  riskLevel: "high" | "medium" | "low";
}

const riskLevelUi: Record<RiskLevelBadgeProps["riskLevel"], { label: string; className: string }> = {
  high: {
    label: "Yüksek Risk",
    className: "bg-rose-100 text-rose-700 border-rose-200",
  },
  medium: {
    label: "Orta Risk",
    className: "bg-amber-100 text-amber-700 border-amber-200",
  },
  low: {
    label: "Düşük Risk",
    className: "bg-emerald-100 text-emerald-700 border-emerald-200",
  },
};

export default function RiskLevelBadge({ riskLevel }: RiskLevelBadgeProps) {
  const ui = riskLevelUi[riskLevel];

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${ui.className}`}
    >
      {ui.label}
    </span>
  );
}
