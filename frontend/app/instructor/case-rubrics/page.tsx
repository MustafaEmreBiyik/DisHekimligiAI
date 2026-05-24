"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { caseRubricAPI, CaseRubric, DecisionPoint } from "@/lib/api";
import {
  AlertTriangle,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  MinusCircle,
  Shield,
  Star,
} from "lucide-react";

// ── Helpers ──────────────────────────────────────────────────────────────────

function levelBadge(level: DecisionPoint["rubric_level"]) {
  if (level === "critical") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">
        <Shield className="h-3 w-3" />
        Kritik
      </span>
    );
  }
  if (level === "penalty") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-semibold text-orange-700">
        <MinusCircle className="h-3 w-3" />
        Ceza
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-700">
      <Star className="h-3 w-3" />
      Standart
    </span>
  );
}

function scoreBadge(score: number) {
  const colour =
    score > 0
      ? "bg-blue-50 text-blue-700 border-blue-200"
      : "bg-red-50 text-red-700 border-red-200";
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 text-xs font-bold tabular-nums ${colour}`}
    >
      {score > 0 ? `+${score}` : score} pts
    </span>
  );
}

// ── Sub-component: single case rubric card ───────────────────────────────────

function CaseRubricCard({ rubric }: { rubric: CaseRubric }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Header row */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-4 rounded-2xl p-5 text-left transition hover:bg-slate-50"
      >
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-semibold text-slate-800">
              {rubric.case_id}
            </span>
            {rubric.critical_count > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                <AlertTriangle className="h-3 w-3" />
                {rubric.critical_count} kritik nokta
              </span>
            )}
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-500">
            <span>Maks puan: <strong>{rubric.total_max_score}</strong></span>
            <span>Adım: <strong>{rubric.positive_count}</strong></span>
            <span>Ceza: <strong>{rubric.penalty_count}</strong></span>
          </div>
        </div>
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
        )}
      </button>

      {/* Expanded decision points table */}
      {open && (
        <div className="border-t border-slate-100 px-5 pb-5">
          {/* Summary row */}
          <div className="mb-4 mt-4 flex flex-wrap gap-2">
            <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700">
              {rubric.critical_count} kritik
            </span>
            <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
              {rubric.positive_count} standart
            </span>
            <span className="rounded-full bg-orange-50 px-3 py-1 text-xs font-medium text-orange-700">
              {rubric.penalty_count} ceza
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Aksiyon</th>
                  <th className="pb-2 pr-4">Sonuç</th>
                  <th className="pb-2 pr-4">Puan</th>
                  <th className="pb-2 pr-4">Seviye</th>
                  <th className="pb-2">Yetkinlikler</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {rubric.decision_points.map((dp: DecisionPoint) => (
                  <tr
                    key={dp.target_action}
                    className={
                      dp.is_critical
                        ? "bg-red-50/40"
                        : dp.rubric_level === "penalty"
                        ? "bg-orange-50/30"
                        : ""
                    }
                  >
                    <td className="py-2.5 pr-4 font-mono text-xs text-slate-700">
                      {dp.target_action}
                    </td>
                    <td className="py-2.5 pr-4 text-slate-600">{dp.rule_outcome}</td>
                    <td className="py-2.5 pr-4">{scoreBadge(dp.score)}</td>
                    <td className="py-2.5 pr-4">{levelBadge(dp.rubric_level)}</td>
                    <td className="py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {dp.competency_tags.map((tag: string) => (
                          <span
                            key={tag}
                            className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                          >
                            {tag}
                          </span>
                        ))}
                        {dp.safety_category && (
                          <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">
                            safety: {dp.safety_category}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CaseRubricsPage() {
  const [rubrics, setRubrics] = useState<CaseRubric[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterLevel, setFilterLevel] = useState<"all" | "critical_only">("all");

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const data = await caseRubricAPI.getAllRubrics();
        setRubrics(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Vaka rubriği yüklenemedi.");
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []);

  const displayed =
    filterLevel === "critical_only"
      ? rubrics.filter((r) => r.critical_count > 0)
      : rubrics;

  const totalCritical = rubrics.reduce((n, r) => n + r.critical_count, 0);

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-5xl space-y-6">
          {/* Header */}
          <header className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="mb-1 flex items-center gap-2 text-sm text-slate-500">
                  <Link
                    href="/instructor/dashboard"
                    className="flex items-center gap-1 hover:text-slate-700"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Dashboard
                  </Link>
                </div>
                <h1 className="text-2xl font-bold text-slate-900">
                  Vaka Rubrik Yönetimi
                </h1>
                <p className="mt-1 text-sm text-slate-500">
                  Klinik simülasyon vakalarının kritik karar noktaları ve puanlama rubriği
                </p>
              </div>

              {!isLoading && rubrics.length > 0 && (
                <div className="flex shrink-0 flex-col gap-1 text-right text-sm">
                  <span className="font-semibold text-slate-700">
                    {rubrics.length} vaka
                  </span>
                  {totalCritical > 0 && (
                    <span className="flex items-center justify-end gap-1 text-red-600">
                      <AlertTriangle className="h-4 w-4" />
                      {totalCritical} toplam kritik nokta
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Legend */}
            <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-4 text-xs">
              <span className="flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5 text-red-500" />
                <span className="text-slate-600">Kritik — hastaya zarar verebilir, eksikse ağır puan kaybı</span>
              </span>
              <span className="flex items-center gap-1.5">
                <Star className="h-3.5 w-3.5 text-green-500" />
                <span className="text-slate-600">Standart — doğru klinik adım</span>
              </span>
              <span className="flex items-center gap-1.5">
                <MinusCircle className="h-3.5 w-3.5 text-orange-500" />
                <span className="text-slate-600">Ceza — yanlış/zararlı eylem (eksi puan)</span>
              </span>
            </div>
          </header>

          {/* Filter bar */}
          {!isLoading && rubrics.length > 0 && (
            <div className="flex gap-2">
              <button
                onClick={() => setFilterLevel("all")}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  filterLevel === "all"
                    ? "bg-slate-800 text-white"
                    : "bg-white text-slate-600 border border-slate-300 hover:bg-slate-50"
                }`}
              >
                Tümü ({rubrics.length})
              </button>
              <button
                onClick={() => setFilterLevel("critical_only")}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  filterLevel === "critical_only"
                    ? "bg-red-600 text-white"
                    : "bg-white text-slate-600 border border-slate-300 hover:bg-slate-50"
                }`}
              >
                Yalnızca Kritik ({rubrics.filter((r) => r.critical_count > 0).length})
              </button>
            </div>
          )}

          {/* Content */}
          {isLoading ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
              Yükleniyor…
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
              {error}
            </div>
          ) : displayed.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center text-sm text-slate-500">
              {filterLevel === "critical_only"
                ? "Kritik karar noktası olan vaka bulunamadı."
                : "Henüz vaka rubriği tanımlı değil."}
            </div>
          ) : (
            <div className="space-y-4">
              {displayed.map((rubric) => (
                <CaseRubricCard key={rubric.case_id} rubric={rubric} />
              ))}
            </div>
          )}
        </div>
      </div>
        </InstructorRouteGuard>
  );
}
