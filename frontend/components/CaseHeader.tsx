"use client";

/**
 * Case Header Component
 * =====================
 * Displays case context (patient info, difficulty) at top of chat.
 */

import React from "react";

interface CaseHeaderProps {
  caseName: string | null | undefined;
  difficulty: string | null | undefined;
  patientAge: number | null | undefined;
  chiefComplaint: string | null | undefined;
}

export default function CaseHeader({
  caseName,
  difficulty,
  patientAge,
  chiefComplaint,
}: CaseHeaderProps) {
  // Difficulty badge color
  const getDifficultyColor = (diff: string | null) => {
    if (!diff) return "bg-gray-100 text-gray-600";

    const d = diff.toLowerCase();
    if (d === "kolay" || d === "easy") {
      return "bg-green-100 text-green-700";
    } else if (d === "orta" || d === "medium") {
      return "bg-yellow-100 text-yellow-700";
    } else if (d === "zor" || d === "hard" || d === "difficult") {
      return "bg-red-100 text-red-700";
    }
    return "bg-gray-100 text-gray-600";
  };

  return (
    <div className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
      <div className="max-w-4xl mx-auto px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Case Name */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-md">
              <span className="text-white text-lg">📋</span>
            </div>
            <div>
              <h2 className="font-bold text-gray-900">{caseName || "Vaka"}</h2>
              {difficulty && (
                <span
                  className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${getDifficultyColor(
                    difficulty
                  )}`}
                >
                  {difficulty}
                </span>
              )}
            </div>
          </div>

          {/* Patient Info */}
          <div className="flex items-center gap-4 text-sm text-gray-600">
            {patientAge && (
              <div className="flex items-center gap-1">
                <span>👤</span>
                <span>{patientAge} yaş</span>
              </div>
            )}
            {chiefComplaint && (
              <div className="flex items-center gap-1 max-w-xs">
                <span>💬</span>
                <span className="truncate" title={chiefComplaint}>
                  {chiefComplaint.length > 50
                    ? chiefComplaint.substring(0, 50) + "..."
                    : chiefComplaint}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
