"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  InstructorStudentDrilldownResponse,
  casesAPI,
  instructorAPI,
} from "@/lib/api";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import RiskLevelBadge from "@/components/instructor/RiskLevelBadge";

interface CaseOption {
  case_id: string;
  title: string;
}

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

function reasonCodeLabel(reasonCode: string): string {
  if (reasonCode === "instructor_spotlight") {
    return "Eğitmen Spotlight";
  }
  if (reasonCode === "weak_competency") {
    return "Zayıf Yetkinlik";
  }
  if (reasonCode === "cold_start") {
    return "Başlangıç";
  }
  if (reasonCode === "not_attempted") {
    return "Henüz Denenmedi";
  }
  if (reasonCode === "difficulty_match") {
    return "Zorluk Uyumu";
  }
  return reasonCode;
}

export default function InstructorStudentDetailPage() {
  const params = useParams<{ student_id: string }>();
  const studentId = String(params.student_id || "");

  const [drilldown, setDrilldown] =
    useState<InstructorStudentDrilldownResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showStudentHeader, setShowStudentHeader] = useState(true);
  const [showSessions, setShowSessions] = useState(true);
  const [showRecommendationHistory, setShowRecommendationHistory] = useState(true);
  const [showSpotlightForm, setShowSpotlightForm] = useState(true);

  const [caseOptions, setCaseOptions] = useState<CaseOption[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [spotlightReason, setSpotlightReason] = useState("");
  const [isSubmittingSpotlight, setIsSubmittingSpotlight] = useState(false);
  const [spotlightSuccessMessage, setSpotlightSuccessMessage] = useState("");
  const [spotlightErrorMessage, setSpotlightErrorMessage] = useState("");

  const loadDrilldown = useCallback(async () => {
    setIsLoading(true);

    try {
      const response = await instructorAPI.getStudentDrilldown(studentId);
      setDrilldown(response);
      setShowStudentHeader(true);
      setShowSessions(true);
      setShowRecommendationHistory(true);
      setShowSpotlightForm(true);
    } catch {
      setDrilldown(null);
      setShowStudentHeader(false);
      setShowSessions(false);
      setShowRecommendationHistory(false);
      setShowSpotlightForm(false);
    } finally {
      setIsLoading(false);
    }
  }, [studentId]);

  useEffect(() => {
    if (!studentId) {
      setIsLoading(false);
      setShowStudentHeader(false);
      setShowSessions(false);
      setShowRecommendationHistory(false);
      setShowSpotlightForm(false);
      return;
    }

    loadDrilldown();
  }, [loadDrilldown, studentId]);

  useEffect(() => {
    const loadCaseOptions = async () => {
      try {
        const allCases = await casesAPI.getAllCases();
        if (!Array.isArray(allCases)) {
          return;
        }

        const normalized: CaseOption[] = allCases
          .map((item: { case_id?: string; name?: string }) => ({
            case_id: item.case_id ?? "",
            title: item.name ?? item.case_id ?? "",
          }))
          .filter((item: CaseOption) => item.case_id.length > 0);

        if (normalized.length > 0) {
          setCaseOptions(normalized);
        }
      } catch {
        // Sessiz fail: Vaka listesi yüklenmezse mevcut veri ile devam.
      }
    };

    loadCaseOptions();
  }, []);

  const derivedCaseOptions = useMemo(() => {
    const map = new Map<string, string>();

    drilldown?.sessions.forEach((item) => {
      if (!map.has(item.case_id)) {
        map.set(item.case_id, item.case_title);
      }
    });

    drilldown?.recommendation_history.forEach((item) => {
      if (!map.has(item.case_id)) {
        map.set(item.case_id, item.case_id);
      }
    });

    caseOptions.forEach((item) => {
      map.set(item.case_id, item.title);
    });

    return Array.from(map.entries()).map(([case_id, title]) => ({
      case_id,
      title,
    }));
  }, [caseOptions, drilldown?.recommendation_history, drilldown?.sessions]);

  useEffect(() => {
    if (!selectedCaseId && derivedCaseOptions.length > 0) {
      setSelectedCaseId(derivedCaseOptions[0].case_id);
    }
  }, [derivedCaseOptions, selectedCaseId]);

  const handleSpotlightSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!selectedCaseId || !spotlightReason.trim()) {
      return;
    }

    setSpotlightSuccessMessage("");
    setSpotlightErrorMessage("");
    setIsSubmittingSpotlight(true);

    try {
      const response = await instructorAPI.createSpotlight(studentId, {
        case_id: selectedCaseId,
        reason: spotlightReason.trim(),
      });

      setSpotlightSuccessMessage(response.message);
      setSpotlightReason("");

      await loadDrilldown();
    } catch {
      setSpotlightErrorMessage("Spotlight eklenemedi. Lütfen tekrar deneyin.");
    } finally {
      setIsSubmittingSpotlight(false);
    }
  };

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">
          <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/instructor/dashboard"
                className="inline-flex rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Panele Dön
              </Link>
              <h1 className="text-2xl font-bold text-slate-900">Öğrenci Drill-down</h1>
            </div>
          </header>

          {isLoading && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 text-slate-600">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
                <span className="text-sm font-medium">Öğrenci verileri yükleniyor...</span>
              </div>
            </section>
          )}

          {!isLoading && showStudentHeader && drilldown && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xl font-bold text-slate-900">{drilldown.student.display_name}</h2>
                <RiskLevelBadge riskLevel={drilldown.student.risk_level} />
              </div>

              <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-700 sm:grid-cols-2">
                <p>Öğrenci ID: {drilldown.student.user_id}</p>
                <p>Ortalama Puan: {drilldown.student.avg_score.toFixed(2)}</p>
              </div>

              <div className="mt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Zayıf Yetkinlikler
                </p>
                <div className="flex flex-wrap gap-2">
                  {drilldown.student.weak_competencies.length > 0 ? (
                    drilldown.student.weak_competencies.map((tag) => (
                      <span
                        key={`${drilldown.student.user_id}-${tag}`}
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
            </section>
          )}

          {!isLoading && showSessions && drilldown && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Oturum Geçmişi</h2>

              <div className="overflow-x-auto">
                <table className="min-w-full border-separate border-spacing-y-2">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                      <th className="px-3 py-2">Vaka</th>
                      <th className="px-3 py-2">Skor</th>
                      <th className="px-3 py-2">Tamamlandı</th>
                      <th className="px-3 py-2">Hint</th>
                      <th className="px-3 py-2">Güvenlik İhlali</th>
                      <th className="px-3 py-2">Detay</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drilldown.sessions.map((session) => (
                      <tr key={session.session_id} className="bg-slate-50 text-sm text-slate-800">
                        <td className="px-3 py-2">
                          <p className="font-medium">{session.case_title}</p>
                          <p className="text-xs text-slate-500">{formatDate(session.created_at)}</p>
                        </td>
                        <td className="px-3 py-2">{session.score.toFixed(2)}</td>
                        <td className="px-3 py-2">
                          {session.is_finished ? "Evet" : "Hayır"}
                        </td>
                        <td className="px-3 py-2">{session.hint_count}</td>
                        <td className="px-3 py-2">{session.safety_flags.length}</td>
                        <td className="px-3 py-2">
                          <Link
                            href={`/instructor/sessions/${session.session_id}`}
                            className="inline-flex rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
                          >
                            Detay
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {!isLoading && showRecommendationHistory && drilldown && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Öneri Geçmişi</h2>

              <div className="space-y-3">
                {drilldown.recommendation_history.map((item, index) => (
                  <article
                    key={`${item.case_id}-${item.created_at ?? index}`}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-900">
                        {reasonCodeLabel(item.reason_code)}
                      </p>
                      <div className="flex items-center gap-2">
                        {item.is_spotlight && (
                          <span className="rounded-full bg-cyan-100 px-2.5 py-1 text-xs font-semibold text-cyan-700">
                            Spotlight
                          </span>
                        )}
                        <span className="text-xs text-slate-500">{formatDate(item.created_at)}</span>
                      </div>
                    </div>
                    <p className="mt-1 text-sm text-slate-700">Vaka: {item.case_id}</p>
                    <p className="mt-1 text-sm text-slate-700">{item.reason_text}</p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {!isLoading && showSpotlightForm && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Spotlight Ekle</h2>

              <form className="space-y-4" onSubmit={handleSpotlightSubmit}>
                <div>
                  <label
                    htmlFor="spotlight-case"
                    className="mb-2 block text-sm font-medium text-slate-700"
                  >
                    Vaka Seçimi
                  </label>
                  <select
                    id="spotlight-case"
                    value={selectedCaseId}
                    onChange={(event) => setSelectedCaseId(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                    disabled={derivedCaseOptions.length === 0}
                  >
                    {derivedCaseOptions.map((option) => (
                      <option key={option.case_id} value={option.case_id}>
                        {option.title} ({option.case_id})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="spotlight-reason"
                    className="mb-2 block text-sm font-medium text-slate-700"
                  >
                    Sebep Metni
                  </label>
                  <textarea
                    id="spotlight-reason"
                    rows={4}
                    value={spotlightReason}
                    onChange={(event) => setSpotlightReason(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                    placeholder="Bu spotlight önerisi neden eklendi?"
                  />
                </div>

                {spotlightSuccessMessage && (
                  <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                    {spotlightSuccessMessage}
                  </p>
                )}

                {spotlightErrorMessage && (
                  <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                    {spotlightErrorMessage}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={
                    isSubmittingSpotlight ||
                    !selectedCaseId ||
                    spotlightReason.trim().length === 0
                  }
                  className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSubmittingSpotlight ? "Ekleniyor..." : "Spotlight Ekle"}
                </button>
              </form>
            </section>
          )}
        </div>
      </div>
    </InstructorRouteGuard>
  );
}
