"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  InstructorSessionDetailResponse,
  instructorAPI,
} from "@/lib/api";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";

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

function clinicalAccuracyLabel(value: boolean | null): string {
  if (value === true) {
    return "Klinik Olarak Doğru";
  }
  if (value === false) {
    return "Klinik Olarak Riskli";
  }
  return "Belirsiz";
}

function clinicalAccuracyClass(value: boolean | null): string {
  if (value === true) {
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }
  if (value === false) {
    return "bg-rose-100 text-rose-700 border-rose-200";
  }
  return "bg-slate-100 text-slate-700 border-slate-200";
}

export default function InstructorSessionDetailPage() {
  const params = useParams<{ session_id: string }>();
  const sessionId = String(params.session_id || "");

  const [detail, setDetail] = useState<InstructorSessionDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showSummary, setShowSummary] = useState(true);
  const [showTimeline, setShowTimeline] = useState(true);
  const [showValidatorNotes, setShowValidatorNotes] = useState(true);
  const [showCoachHints, setShowCoachHints] = useState(true);

  useEffect(() => {
    if (!sessionId) {
      setIsLoading(false);
      setShowSummary(false);
      setShowTimeline(false);
      setShowValidatorNotes(false);
      setShowCoachHints(false);
      return;
    }

    const loadSessionDetail = async () => {
      setIsLoading(true);

      try {
        const response = await instructorAPI.getSessionDetail(sessionId);
        setDetail(response);
        setShowSummary(true);
        setShowTimeline(true);
        setShowValidatorNotes(true);
        setShowCoachHints(true);
      } catch {
        setDetail(null);
        setShowSummary(false);
        setShowTimeline(false);
        setShowValidatorNotes(false);
        setShowCoachHints(false);
      } finally {
        setIsLoading(false);
      }
    };

    loadSessionDetail();
  }, [sessionId]);

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
              <h1 className="text-2xl font-bold text-slate-900">Oturum Detayı</h1>
            </div>
          </header>

          {isLoading && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 text-slate-600">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
                <span className="text-sm font-medium">Oturum verileri yükleniyor...</span>
              </div>
            </section>
          )}

          {!isLoading && showSummary && detail && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Oturum Özet Kartı</h2>
              <div className="grid grid-cols-1 gap-3 text-sm text-slate-700 sm:grid-cols-3">
                <p>
                  <span className="font-semibold">Oturum ID:</span> {detail.session_id}
                </p>
                <p>
                  <span className="font-semibold">Öğrenci ID:</span> {detail.student_id}
                </p>
                <p>
                  <span className="font-semibold">Vaka ID:</span> {detail.case_id}
                </p>
                <p>
                  <span className="font-semibold">Skor:</span> {detail.score.toFixed(2)}
                </p>
                <p>
                  <span className="font-semibold">Tamamlandı:</span> {detail.is_finished ? "Evet" : "Hayır"}
                </p>
              </div>
            </section>
          )}

          {!isLoading && showTimeline && detail && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Aksiyon Zaman Çizelgesi</h2>

              <div className="space-y-3">
                {detail.actions.map((action) => (
                  <article
                    key={action.message_id}
                    className={`rounded-xl border p-4 ${
                      action.is_critical_safety_rule
                        ? "border-rose-200 bg-rose-50"
                        : "border-slate-200 bg-slate-50"
                    }`}
                  >
                    <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                      <span className="font-semibold text-slate-700">{formatDate(action.timestamp)}</span>
                      {action.is_critical_safety_rule && (
                        <span className="rounded-full bg-rose-100 px-2.5 py-1 font-semibold text-rose-700">
                          Kritik Güvenlik Kuralı
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-slate-800">
                      <span className="font-semibold">Öğrenci Mesajı:</span> {action.student_message || "-"}
                    </p>
                    <p className="mt-1 text-sm text-slate-800">
                      <span className="font-semibold">Yorumlanan Aksiyon:</span> {action.interpreted_action}
                    </p>
                    <p className="mt-1 text-sm text-slate-800">
                      <span className="font-semibold">Skor Değişimi:</span> {action.score_delta.toFixed(2)}
                    </p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {!isLoading && showValidatorNotes && detail && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Validator Notları</h2>

              <div className="space-y-3">
                {detail.validator_notes.map((note, index) => (
                  <article
                    key={`${note.created_at ?? index}-${index}`}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${clinicalAccuracyClass(
                          note.clinical_accuracy,
                        )}`}
                      >
                        {clinicalAccuracyLabel(note.clinical_accuracy)}
                      </span>
                      <span className="text-xs text-slate-500">{formatDate(note.created_at)}</span>
                    </div>

                    <p className="text-sm text-slate-800">
                      <span className="font-semibold">Güvenlik İhlali:</span>{" "}
                      {note.safety_violation ? "Evet" : "Hayır"}
                    </p>

                    <div className="mt-2">
                      <p className="text-sm font-semibold text-slate-800">Eksik Kritik Adımlar</p>
                      {note.missing_critical_steps.length > 0 ? (
                        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                          {note.missing_critical_steps.map((step) => (
                            <li key={step}>{step}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-1 text-sm text-slate-500">Eksik kritik adım kaydı yok</p>
                      )}
                    </div>

                    <div className="mt-2 rounded-lg bg-white px-3 py-2 text-sm text-slate-700">
                      <span className="font-semibold">Fakülte Notları:</span>{" "}
                      {note.faculty_notes || "Not girilmemiş"}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}

          {!isLoading && showCoachHints && detail && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Koç İpuçları</h2>

              <div className="space-y-3">
                {detail.coach_hints.map((hint, index) => (
                  <article
                    key={`${hint.created_at ?? index}-${hint.hint_level}`}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <span className="rounded-full bg-cyan-100 px-2.5 py-1 text-xs font-semibold text-cyan-700">
                        {hint.hint_level}
                      </span>
                      <span className="text-xs text-slate-500">{formatDate(hint.created_at)}</span>
                    </div>
                    <p className="text-sm text-slate-800">{hint.content}</p>
                  </article>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </InstructorRouteGuard>
  );
}
