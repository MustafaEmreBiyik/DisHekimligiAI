"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  InstructorSessionDetailResponse,
  CognitiveLoadResponse,
  SafetyMetricsResponse,
  ProcessTraceResponse,
  instructorAPI,
} from "@/lib/api";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";

function formatDate(dateText: string | null): string {
  if (!dateText) return "-";
  const date = new Date(dateText);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function clinicalAccuracyLabel(value: boolean | null): string {
  if (value === true) return "Klinik Olarak Doğru";
  if (value === false) return "Klinik Olarak Riskli";
  return "Belirsiz";
}

function clinicalAccuracyClass(value: boolean | null): string {
  if (value === true) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (value === false) return "bg-rose-100 text-rose-700 border-rose-200";
  return "bg-slate-100 text-slate-700 border-slate-200";
}

// ── S10-D helpers ─────────────────────────────────────────────────────────────

function loadLevelClass(level: string): string {
  if (level === "low") return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (level === "medium") return "bg-amber-100 text-amber-700 border-amber-200";
  return "bg-rose-100 text-rose-700 border-rose-200";
}

function loadLevelLabel(level: string): string {
  if (level === "low") return "Düşük";
  if (level === "medium") return "Orta";
  return "Yüksek";
}

function formatMs(ms: number | null): string {
  if (ms === null) return "-";
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(1)} sn`;
}

// ── S10-F helpers ─────────────────────────────────────────────────────────────

function roleLabel(role: string): string {
  if (role === "user") return "Öğrenci";
  if (role === "assistant") return "Asistan";
  return role;
}

function roleClass(role: string): string {
  if (role === "user") return "bg-blue-100 text-blue-700 border-blue-200";
  if (role === "assistant") return "bg-violet-100 text-violet-700 border-violet-200";
  return "bg-slate-100 text-slate-700 border-slate-200";
}

function safetyActionLabel(action: string): string {
  const map: Record<string, string> = {
    ask_allergies: "Alerji Sorgulama",
    ask_medications: "İlaç Sorgulama",
    ask_medical_history: "Tıbbi Geçmiş Sorgulama",
  };
  return map[action] ?? action;
}

// ─────────────────────────────────────────────────────────────────────────────

export default function InstructorSessionDetailPage() {
  const params = useParams<{ session_id: string }>();
  const sessionId = String(params.session_id || "");

  const [detail, setDetail] = useState<InstructorSessionDetailResponse | null>(null);
  const [cognitiveLoad, setCognitiveLoad] = useState<CognitiveLoadResponse | null>(null);
  const [safetyMetrics, setSafetyMetrics] = useState<SafetyMetricsResponse | null>(null);
  const [processTrace, setProcessTrace] = useState<ProcessTraceResponse | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setIsLoading(false);
      return;
    }

    const load = async () => {
      setIsLoading(true);
      setAnalyticsError(null);

      // Core session detail — primary fetch
      const detailResult = await instructorAPI.getSessionDetail(sessionId).catch(() => null);
      setDetail(detailResult);

      // Analytics panels — load in parallel, tolerate failures individually
      const [clResult, smResult, ptResult] = await Promise.allSettled([
        instructorAPI.getSessionCognitiveLoad(sessionId),
        instructorAPI.getSessionSafetyMetrics(sessionId),
        instructorAPI.getSessionProcessTrace(sessionId),
      ]);

      if (clResult.status === "fulfilled") setCognitiveLoad(clResult.value);
      if (smResult.status === "fulfilled") setSafetyMetrics(smResult.value);
      if (ptResult.status === "fulfilled") setProcessTrace(ptResult.value);

      const anyFailed = [clResult, smResult, ptResult].some((r) => r.status === "rejected");
      if (anyFailed) setAnalyticsError("Bazı analitik paneller yüklenemedi.");

      setIsLoading(false);
    };

    load();
  }, [sessionId]);

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">

          {/* Header */}
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

          {analyticsError && !isLoading && (
            <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
              {analyticsError}
            </p>
          )}

          {/* ── Oturum Özet Kartı ─────────────────────────────────────────── */}
          {!isLoading && detail && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Oturum Özet Kartı</h2>
              <div className="grid grid-cols-1 gap-3 text-sm text-slate-700 sm:grid-cols-3">
                <p><span className="font-semibold">Oturum ID:</span> {detail.session_id}</p>
                <p><span className="font-semibold">Öğrenci ID:</span> {detail.student_id}</p>
                <p><span className="font-semibold">Vaka ID:</span> {detail.case_id}</p>
                <p><span className="font-semibold">Skor:</span> {detail.score.toFixed(2)}</p>
                <p><span className="font-semibold">Tamamlandı:</span> {detail.is_finished ? "Evet" : "Hayır"}</p>
              </div>
            </section>
          )}

          {/* ── S10-D: Bilişsel Yük Profili ───────────────────────────────── */}
          {!isLoading && cognitiveLoad && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <h2 className="text-xl font-bold text-slate-900">Bilişsel Yük Profili</h2>
                <span
                  className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${loadLevelClass(cognitiveLoad.load_level)}`}
                >
                  {loadLevelLabel(cognitiveLoad.load_level)}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                  <p className="text-2xl font-bold text-slate-800">
                    {formatMs(cognitiveLoad.avg_response_time_ms)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Ort. Yanıt Süresi</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                  <p className="text-2xl font-bold text-slate-800">{cognitiveLoad.hint_count}</p>
                  <p className="mt-1 text-xs text-slate-500">İpucu Kullanımı</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                  <p className="text-2xl font-bold text-slate-800">{cognitiveLoad.action_count}</p>
                  <p className="mt-1 text-xs text-slate-500">Toplam Aksiyon</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                  <p className="text-2xl font-bold text-slate-800">{cognitiveLoad.deviation_count}</p>
                  <p className="mt-1 text-xs text-slate-500">Sapma Sayısı</p>
                </div>
              </div>
              {cognitiveLoad.action_count > 0 && (
                <div className="mt-4">
                  <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                    <span>Sapma Oranı</span>
                    <span>
                      {((cognitiveLoad.deviation_count / cognitiveLoad.action_count) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-2 rounded-full bg-rose-400"
                      style={{
                        width: `${Math.min(
                          100,
                          (cognitiveLoad.deviation_count / cognitiveLoad.action_count) * 100,
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              )}
              <p className="mt-3 text-right text-xs text-slate-400">
                Hesaplandı: {formatDate(cognitiveLoad.computed_at)}
              </p>
            </section>
          )}

          {/* ── S10-E: Güvenlik Kritik Aksiyon Metrikleri ─────────────────── */}
          {!isLoading && safetyMetrics && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <h2 className="text-xl font-bold text-slate-900">Güvenlik Kritik Aksiyonlar</h2>
                <span
                  className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${
                    safetyMetrics.all_safety_checks_done
                      ? "bg-emerald-100 text-emerald-700 border-emerald-200"
                      : "bg-rose-100 text-rose-700 border-rose-200"
                  }`}
                >
                  {safetyMetrics.all_safety_checks_done ? "Tüm Kontroller Tamamlandı" : "Eksik Kontroller Var"}
                </span>
              </div>

              <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                {/* Yapılan güvenlik aksiyonları */}
                <div>
                  <p className="mb-2 text-sm font-semibold text-emerald-700">
                    Yapılan Güvenlik Kontrolleri ({safetyMetrics.safety_actions_taken.length})
                  </p>
                  {safetyMetrics.safety_actions_taken.length > 0 ? (
                    <ul className="space-y-1">
                      {safetyMetrics.safety_actions_taken.map((a) => (
                        <li
                          key={a}
                          className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
                        >
                          <span className="text-emerald-500">✓</span>
                          {safetyActionLabel(a)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-400">Güvenlik aksiyonu yok</p>
                  )}
                </div>

                {/* Eksik güvenlik aksiyonları */}
                <div>
                  <p className="mb-2 text-sm font-semibold text-rose-700">
                    Eksik Güvenlik Kontrolleri ({safetyMetrics.safety_actions_missing.length})
                  </p>
                  {safetyMetrics.safety_actions_missing.length > 0 ? (
                    <ul className="space-y-1">
                      {safetyMetrics.safety_actions_missing.map((a) => (
                        <li
                          key={a}
                          className="flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800"
                        >
                          <span className="text-rose-500">✗</span>
                          {safetyActionLabel(a)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-400">Eksik kontrol yok</p>
                  )}
                </div>
              </div>

              {safetyMetrics.first_safety_action_seconds !== null && (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="text-sm text-slate-700">
                    <span className="font-semibold">İlk Güvenlik Aksiyonuna Süre:</span>{" "}
                    {safetyMetrics.first_safety_action_seconds < 60
                      ? `${safetyMetrics.first_safety_action_seconds} saniye`
                      : `${(safetyMetrics.first_safety_action_seconds / 60).toFixed(1)} dakika`}
                  </p>
                </div>
              )}

              <p className="mt-3 text-right text-xs text-slate-400">
                Hesaplandı: {formatDate(safetyMetrics.computed_at)}
              </p>
            </section>
          )}

          {/* ── S10-F: Tanısal Akıl Yürütme Süreç İzi ────────────────────── */}
          {!isLoading && processTrace && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <h2 className="text-xl font-bold text-slate-900">Tanısal Akıl Yürütme Süreci</h2>
                <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                  {processTrace.total_actions} aksiyon
                </span>
                {processTrace.deviation_count > 0 && (
                  <span className="rounded-full border border-amber-200 bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                    {processTrace.deviation_count} sapma
                  </span>
                )}
              </div>

              {/* Reasoning pattern özeti */}
              {processTrace.reasoning_pattern && (
                <div className="mb-4 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3">
                  <p className="mb-1 text-xs font-bold text-indigo-700">Akıl Yürütme Örüntüsü</p>
                  <div className="grid grid-cols-2 gap-2 text-xs text-indigo-800 sm:grid-cols-4">
                    {Object.entries(processTrace.reasoning_pattern).map(([k, v]) => (
                      <p key={k}>
                        <span className="font-semibold">{k}:</span> {String(v)}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeline */}
              <div className="space-y-2">
                {processTrace.events.map((event) => {
                  const isAction =
                    event.interpreted_action &&
                    !["general_chat", "error", "unknown"].includes(event.interpreted_action);
                  return (
                    <article
                      key={event.seq}
                      className={`rounded-xl border p-3 ${
                        event.reasoning_deviation === true
                          ? "border-amber-200 bg-amber-50"
                          : isAction
                          ? "border-violet-200 bg-violet-50"
                          : "border-slate-200 bg-slate-50"
                      }`}
                    >
                      <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
                        <span className="font-mono text-slate-400">#{event.seq}</span>
                        <span
                          className={`rounded-full border px-2 py-0.5 font-semibold ${roleClass(event.role)}`}
                        >
                          {roleLabel(event.role)}
                        </span>
                        {event.interpreted_action && (
                          <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 font-mono text-slate-600">
                            {event.interpreted_action}
                          </span>
                        )}
                        {event.reasoning_deviation === true && (
                          <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 font-semibold text-amber-700">
                            Sapma
                          </span>
                        )}
                        {event.score !== null && (
                          <span className="ml-auto rounded-full border border-slate-200 bg-white px-2 py-0.5 font-semibold text-slate-700">
                            Δ {event.score >= 0 ? "+" : ""}{event.score.toFixed(2)}
                          </span>
                        )}
                        <span className="text-slate-400">{formatDate(event.timestamp)}</span>
                      </div>
                      <p className="text-sm text-slate-700">{event.content_preview}</p>
                      {event.clinical_intent && (
                        <p className="mt-1 text-xs text-slate-500">
                          <span className="font-semibold">Klinik Niyet:</span> {event.clinical_intent}
                        </p>
                      )}
                    </article>
                  );
                })}
              </div>
            </section>
          )}

          {/* ── Aksiyon Zaman Çizelgesi ────────────────────────────────────── */}
          {!isLoading && detail && detail.actions.length > 0 && (
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
                      <span className="font-semibold">Öğrenci Mesajı:</span>{" "}
                      {action.student_message || "-"}
                    </p>
                    <p className="mt-1 text-sm text-slate-800">
                      <span className="font-semibold">Yorumlanan Aksiyon:</span>{" "}
                      {action.interpreted_action}
                    </p>
                    <p className="mt-1 text-sm text-slate-800">
                      <span className="font-semibold">Skor Değişimi:</span>{" "}
                      {action.score_delta.toFixed(2)}
                    </p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {/* ── Validator Notları ───────────────────────────────────────────── */}
          {!isLoading && detail && detail.validator_notes.length > 0 && (
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
                        className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${clinicalAccuracyClass(note.clinical_accuracy)}`}
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

          {/* ── Koç İpuçları ───────────────────────────────────────────────── */}
          {!isLoading && detail && detail.coach_hints.length > 0 && (
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
