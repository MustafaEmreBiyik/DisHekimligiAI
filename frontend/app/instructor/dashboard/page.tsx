"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  InstructorOverviewResponse,
  InstructorSafetyFlag,
  instructorAPI,
} from "@/lib/api";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import RiskLevelBadge from "@/components/instructor/RiskLevelBadge";

function formatDate(dateText: string | null): string {
  if (!dateText) {
    return "-";
  }

  const date = new Date(dateText);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function SafetyFlagsList({ flags }: { flags: InstructorSafetyFlag[] }) {
  if (flags.length === 0) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900">Güvenlik İhlalleri</h2>
        <span className="text-xs font-medium text-slate-500">Son 10 kritik ihlal</span>
      </div>

      <div className="space-y-3">
        {flags.map((flag) => (
          <div
            key={`${flag.session_id}-${flag.created_at ?? "na"}`}
            className="rounded-xl border border-rose-100 bg-rose-50 p-4"
          >
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-semibold text-slate-900">{flag.display_name}</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-700">Vaka: {flag.case_id}</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-700">{formatDate(flag.created_at)}</span>
            </div>
            <Link
              href={`/instructor/sessions/${flag.session_id}`}
              className="mt-2 inline-flex text-sm font-semibold text-rose-700 hover:text-rose-800"
            >
              Oturuma Git
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function InstructorDashboardPage() {
  const [overview, setOverview] = useState<InstructorOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showStudentsSection, setShowStudentsSection] = useState(true);
  const [showSafetySection, setShowSafetySection] = useState(true);
  const [showCompetencySection, setShowCompetencySection] = useState(true);

  useEffect(() => {
    const loadOverview = async () => {
      setIsLoading(true);

      try {
        const response = await instructorAPI.getOverview();
        setOverview(response);
        setShowStudentsSection(true);
        setShowSafetySection(true);
        setShowCompetencySection(true);
      } catch {
        setOverview(null);
        setShowStudentsSection(false);
        setShowSafetySection(false);
        setShowCompetencySection(false);
      } finally {
        setIsLoading(false);
      }
    };

    loadOverview();
  }, []);

  const safetyFlags = useMemo(
    () => (overview?.safety_flags ?? []).slice(0, 10),
    [overview?.safety_flags],
  );

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">
          <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 className="text-3xl font-bold text-slate-900">Eğitmen Paneli</h1>
            <p className="mt-2 text-sm text-slate-600">
              Öğrenci risk durumları, kritik güvenlik ihlalleri ve yetkinlik özetleri
            </p>
          </header>

          {isLoading && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 text-slate-600">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
                <span className="text-sm font-medium">Panel verileri yükleniyor...</span>
              </div>
            </section>
          )}

          {!isLoading && showStudentsSection && overview && (
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-900">Öğrenci Listesi</h2>
                <span className="text-xs font-medium text-slate-500">
                  Toplam: {overview.assigned_students.length}
                </span>
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {overview.assigned_students.map((student) => (
                  <article
                    key={student.user_id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-lg font-bold text-slate-900">{student.display_name}</h3>
                      <RiskLevelBadge riskLevel={student.risk_level} />
                    </div>

                    <div className="grid grid-cols-1 gap-2 text-sm text-slate-700 sm:grid-cols-2">
                      <p>Ortalama Puan: {student.avg_score.toFixed(2)}</p>
                      <p>Toplam Oturum: {student.total_sessions}</p>
                      <p className="sm:col-span-2">Son Aktivite: {formatDate(student.last_active)}</p>
                    </div>

                    <div className="mt-4">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Zayıf Yetkinlikler
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {student.weak_competencies.length > 0 ? (
                          student.weak_competencies.map((tag) => (
                            <span
                              key={`${student.user_id}-${tag}`}
                              className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
                            >
                              {tag}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500">Belirgin zayıf alan yok</span>
                        )}
                      </div>
                    </div>

                    <Link
                      href={`/instructor/students/${student.user_id}`}
                      className="mt-4 inline-flex items-center rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                    >
                      Detay
                    </Link>
                  </article>
                ))}
              </div>
            </section>
          )}

          {!isLoading && showSafetySection && <SafetyFlagsList flags={safetyFlags} />}

          {!isLoading && showCompetencySection && overview && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Yetkinlik Özet Tablosu</h2>

              <div className="overflow-x-auto">
                <table className="min-w-full border-separate border-spacing-y-2">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                      <th className="px-3 py-2">Yetkinlik Alanı</th>
                      <th className="px-3 py-2">Ortalama Puan</th>
                      <th className="px-3 py-2">Etkilenen Öğrenci</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(overview.competency_summary).map(([tag, item]) => (
                      <tr key={tag} className="rounded-xl bg-slate-50 text-sm text-slate-800">
                        <td className="px-3 py-2 font-medium">{tag}</td>
                        <td className="px-3 py-2">{item.avg_score.toFixed(2)}</td>
                        <td className="px-3 py-2">{item.student_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      </div>
    </InstructorRouteGuard>
  );
}
