"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import {
  quizAPI,
  AttemptListItem,
  QuizSubmitResponse,
  ProgressTimeline,
  ProgressWeek,
  MasteryTopicInfo,
} from "@/lib/api";
import {
  History,
  TrendingUp,
  ChevronRight,
  ArrowLeft,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from "recharts";

// ── Helpers ────────────────────────────────────────────────────────────────────

function irtLabel(theta: number): string {
  if (theta >= 1.5) return "İleri Seviye";
  if (theta >= 0.5) return "Orta-Üst";
  if (theta >= -0.5) return "Orta";
  if (theta >= -1.5) return "Orta-Alt";
  return "Başlangıç";
}

function masteryColor(pct: number): string {
  if (pct >= 70) return "#22c55e";
  if (pct >= 40) return "#f59e0b";
  return "#ef4444";
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-white rounded-xl border p-4 flex flex-col gap-1 shadow-sm">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`text-2xl font-bold ${color ?? "text-gray-800"}`}>{value}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
}

function QuizScoreChart({ weeks }: { weeks: ProgressWeek[] }) {
  const data = weeks.map((w) => ({
    name: w.week_label,
    "Sınav Ortalaması": w.quiz_score_avg ?? undefined,
    "Deneme Sayısı": w.quiz_attempts,
  }));
  return (
    <div className="bg-white rounded-xl border p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">
        Haftalık Sınav Puanı Trendi (%)
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(v: unknown) => (v !== undefined ? `%${v}` : "—")}
          />
          <Area
            type="monotone"
            dataKey="Sınav Ortalaması"
            stroke="#3b82f6"
            fill="url(#scoreGrad)"
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function ActivityChart({ weeks }: { weeks: ProgressWeek[] }) {
  const data = weeks.map((w) => ({
    name: w.week_label,
    "Quiz Denemesi": w.quiz_attempts,
    "Tamamlanan Vaka": w.cases_completed,
  }));
  return (
    <div className="bg-white rounded-xl border p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">
        Haftalık Aktivite (Quiz + Vaka)
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="Quiz Denemesi" fill="#6366f1" radius={[3, 3, 0, 0]} />
          <Bar dataKey="Tamamlanan Vaka" fill="#10b981" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function MasteryChart({
  mastery,
}: {
  mastery: Record<string, MasteryTopicInfo>;
}) {
  const entries = Object.entries(mastery);
  if (entries.length === 0) {
    return (
      <div className="bg-white rounded-xl border p-5 shadow-sm text-center text-gray-400 text-sm py-12">
        Henüz ustalık verisi yok.
      </div>
    );
  }
  const data = entries.map(([, info]) => ({
    name: info.label,
    "Ustalık (%)": info.mastery_pct,
    fill: masteryColor(info.mastery_pct),
  }));
  return (
    <div className="bg-white rounded-xl border p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">
        Konu Bazlı Ustalık Düzeyi
      </h3>
      <ResponsiveContainer width="100%" height={Math.max(140, entries.length * 48)}>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 4, right: 24, left: 8, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v: unknown) => `%${v}`} />
          <Bar dataKey="Ustalık (%)" radius={[0, 4, 4, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-3 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-green-500 inline-block" /> ≥70% Yeterli
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-amber-400 inline-block" /> 40-69% Gelişiyor
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-red-500 inline-block" /> &lt;40% Zayıf
        </span>
      </div>
    </div>
  );
}

function AnalyticsTab() {
  const [timeline, setTimeline] = useState<ProgressTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    quizAPI
      .getMyProgressTimeline(12)
      .then(setTimeline)
      .catch(() => setError("İlerleme verisi yüklenemedi."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg">
        {error}
      </div>
    );
  }

  if (!timeline) return null;

  const { summary } = timeline;

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard
          label="Toplam Quiz Denemesi"
          value={summary.total_quiz_attempts}
          sub="son 12 hafta"
          color="text-indigo-600"
        />
        <SummaryCard
          label="Tamamlanan Vaka"
          value={summary.total_cases_completed}
          sub="son 12 hafta"
          color="text-emerald-600"
        />
        <SummaryCard
          label="Ortalama Quiz Puanı"
          value={
            summary.avg_quiz_score_pct !== null
              ? `%${summary.avg_quiz_score_pct}`
              : "—"
          }
          sub="tamamlanan denemeler"
          color="text-blue-600"
        />
        <SummaryCard
          label="IRT Yetenek Tahmini"
          value={`θ = ${summary.irt_theta_current}`}
          sub={irtLabel(summary.irt_theta_current)}
          color="text-purple-600"
        />
      </div>

      {/* Charts */}
      <QuizScoreChart weeks={timeline.weeks} />
      <ActivityChart weeks={timeline.weeks} />
      <MasteryChart mastery={timeline.mastery_by_topic} />
    </div>
  );
}

// ── History (existing) tab ─────────────────────────────────────────────────────

function HistoryTab() {
  const [attempts, setAttempts] = useState<AttemptListItem[]>([]);
  const [selectedAttempt, setSelectedAttempt] = useState<QuizSubmitResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    quizAPI
      .getMyAttempts()
      .then(setAttempts)
      .catch(() => setError("Geçmiş yüklenemedi."))
      .finally(() => setLoading(false));
  }, []);

  const handleSelect = async (attemptId: number) => {
    try {
      const detail = await quizAPI.getMyAttemptDetail(attemptId);
      setSelectedAttempt(detail);
    } catch {
      setError("Detay yüklenemedi.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (selectedAttempt) {
    return (
      <div>
        <button
          onClick={() => setSelectedAttempt(null)}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-6"
        >
          <ArrowLeft size={18} /> Listeye Dön
        </button>

        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <h2 className="text-xl font-semibold mb-2">
            Deneme #{selectedAttempt.attempt_id}
          </h2>
          <div className="flex gap-6 text-sm text-gray-600">
            <span>Puan: {selectedAttempt.score ?? "—"} / {selectedAttempt.total}</span>
            {selectedAttempt.percentage != null && (
              <span>Başarı: %{selectedAttempt.percentage}</span>
            )}
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                selectedAttempt.overall_status === "PUBLISHED"
                  ? "bg-green-100 text-green-700"
                  : "bg-yellow-100 text-yellow-700"
              }`}
            >
              {selectedAttempt.overall_status === "PUBLISHED" ? "Yayınlandı" : "Bekliyor"}
            </span>
          </div>
        </div>

        <div className="space-y-4">
          {selectedAttempt.results.map((r, i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border p-5">
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  {r.grading_status === "PUBLISHED" ? (
                    r.is_correct ? (
                      <CheckCircle size={20} className="text-green-500" />
                    ) : (
                      <XCircle size={20} className="text-red-500" />
                    )
                  ) : (
                    <Clock size={20} className="text-yellow-500" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800 mb-1">{r.question}</p>
                  <p className="text-sm text-gray-500 mb-2">Cevabınız: {r.selected_option || "—"}</p>
                  {r.feedback && (
                    <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">{r.feedback}</p>
                  )}
                  {r.instructor_score != null && (
                    <p className="text-sm text-blue-600 mt-1">
                      Hoca Puanı: {r.instructor_score}
                    </p>
                  )}
                  {r.instructor_feedback && (
                    <p className="text-sm text-gray-600 mt-1 italic">{r.instructor_feedback}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {attempts.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <History size={48} className="mx-auto mb-4 opacity-30" />
          <p>Henüz sınav denemesi bulunmuyor.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {attempts.map((a) => (
            <button
              key={a.attempt_id}
              onClick={() => handleSelect(a.attempt_id)}
              className="w-full bg-white rounded-xl shadow-sm border p-5 hover:border-blue-300 hover:shadow-md transition-all text-left flex items-center justify-between"
            >
              <div>
                <div className="font-semibold text-gray-800 mb-1">
                  Deneme #{a.attempt_id}
                </div>
                <div className="text-sm text-gray-500 flex gap-4">
                  <span>{new Date(a.created_at).toLocaleDateString("tr-TR")}</span>
                  <span>{a.question_count} soru</span>
                  <span>
                    {a.percentage != null
                      ? `%${a.percentage}`
                      : `${a.total_score}/${a.max_score}`}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                    a.overall_status === "PUBLISHED"
                      ? "bg-green-100 text-green-700"
                      : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {a.overall_status === "PUBLISHED" ? "Yayınlandı" : "Bekliyor"}
                </span>
                <ChevronRight size={18} className="text-gray-400" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "history" | "analytics";

export default function StudentHistoryPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("history");

  if (!user) {
    router.push("/login");
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <History size={28} className="text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-800">Öğrenim Geçmişi</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
        <button
          onClick={() => setTab("history")}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-all ${
            tab === "history"
              ? "bg-white text-blue-700 shadow-sm"
              : "text-gray-600 hover:text-gray-800"
          }`}
        >
          <History size={15} />
          Sınav Geçmişi
        </button>
        <button
          onClick={() => setTab("analytics")}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-all ${
            tab === "analytics"
              ? "bg-white text-blue-700 shadow-sm"
              : "text-gray-600 hover:text-gray-800"
          }`}
        >
          <TrendingUp size={15} />
          İlerleme Analizi
        </button>
      </div>

      {tab === "history" ? <HistoryTab /> : <AnalyticsTab />}
    </div>
  );
}
