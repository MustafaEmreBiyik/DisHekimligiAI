"use client";

import React from "react";

// FDI two-digit notation: quadrant (1-4) + position (1-8)
const QUADRANTS: { label: string; teeth: number[] }[] = [
  { label: "Sağ Üst", teeth: [18, 17, 16, 15, 14, 13, 12, 11] },
  { label: "Sol Üst", teeth: [21, 22, 23, 24, 25, 26, 27, 28] },
  { label: "Sağ Alt", teeth: [48, 47, 46, 45, 44, 43, 42, 41] },
  { label: "Sol Alt", teeth: [31, 32, 33, 34, 35, 36, 37, 38] },
];

interface ToothMapProps {
  highlightedTeeth?: number[];
  onToothClick?: (toothNumber: number) => void;
}

export default function ToothMap({ highlightedTeeth = [], onToothClick }: ToothMapProps) {
  return (
    <div className="select-none text-center">
      <p className="mb-1 text-xs font-semibold text-gray-500 uppercase tracking-wide">
        FDI Diş Haritası
      </p>
      <div className="grid grid-cols-2 gap-1">
        {QUADRANTS.map((q) => (
          <div key={q.label}>
            <p className="text-[10px] text-gray-400 mb-0.5">{q.label}</p>
            <div className="flex gap-0.5 justify-center flex-wrap">
              {q.teeth.map((num) => {
                const active = highlightedTeeth.includes(num);
                return (
                  <button
                    key={num}
                    onClick={() => onToothClick?.(num)}
                    title={`Diş ${num}`}
                    className={`w-7 h-7 rounded text-[10px] font-mono border transition-colors ${
                      active
                        ? "bg-red-400 border-red-500 text-white"
                        : "bg-gray-100 border-gray-200 text-gray-600 hover:bg-blue-100 hover:border-blue-300"
                    }`}
                  >
                    {num}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
