"use client";

import { useEffect, useState } from "react";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { BarChart3, AlertTriangle, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface QuestionStat {
  question_id: number;
  question_text_short: string;
  topic_id: string;
  difficulty: string;
  total_answers: number;
  correct_count: number;
  correct_pct: number;
  avg_ai_score: number | null;
  avg_instructor_score: number | null;
  ai_human_delta: number | null;
}

export default function QuestionStatsPage() {
  const [stats, setStats] = useState<QuestionStat[]>([]);
  const [deltaTop, setDeltaTop] = useState<QuestionStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch(`${API_BASE}/api/quiz/instructor/question-stats`, { headers }).then((r) => r.json()),
      fetch(`${API_BASE}/api/quiz/instructor/ai-vs-human-delta`, { headers }).then((r) => r.json()),
    ])
      .then(([s, d]) => {
        setStats(s as QuestionStat[]);
        setDeltaTop(d as QuestionStat[]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <InstructorRouteGuard>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 size={32} className="animate-spin text-blue-600" />
        </div>
      </InstructorRouteGuard>
    );
  }

  const worstFive = stats.slice(0, 5);

  return (
    <InstructorRouteGuard>
      <div className="max-w-6xl mx-auto p-6 space-y-8">
        <div className="flex items-center gap-3">
          <BarChart3 size={28} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-800">Soru Bazlı İstatistikler</h1>
        </div>

        {/* Worst 5 questions */}
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <AlertTriangle size={20} className="text-red-500" />
            En Sık Yanlış Yapılan 5 Soru
          </h2>
          {worstFive.length === 0 ? (
            <p className="text-gray-500 text-sm">Henüz yeterli veri yok.</p>
          ) : (
            <div className="space-y-3">
              {worstFive.map((q) => (
                <div key={q.question_id} className="flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{q.question_text_short}</p>
                    <p className="text-xs text-gray-500">{q.topic_id} · {q.difficulty}</p>
                  </div>
                  <div className="w-40 flex items-center gap-2">
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${q.correct_pct}%`,
                          backgroundColor: q.correct_pct < 50 ? "#f87171" : q.correct_pct < 75 ? "#fbbf24" : "#34d399",
                        }}
                      />
                    </div>
                    <span className="text-xs font-mono w-12 text-right">{q.correct_pct}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI vs Human delta table */}
        {deltaTop.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="border-b bg-gray-50 px-6 py-3">
              <h2 className="text-lg font-semibold text-gray-800">
                AI vs Eğitmen Skor Farkı (Top 10)
              </h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Soru</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Konu</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-600">AI Ort.</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-600">Eğitmen Ort.</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-600">Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {deltaTop.map((q) => (
                  <tr key={q.question_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 max-w-xs truncate">{q.question_text_short}</td>
                    <td className="px-4 py-2">{q.topic_id}</td>
                    <td className="px-4 py-2 text-right font-mono">{q.avg_ai_score ?? "-"}</td>
                    <td className="px-4 py-2 text-right font-mono">{q.avg_instructor_score ?? "-"}</td>
                    <td className="px-4 py-2 text-right font-mono font-bold text-red-600">{q.ai_human_delta ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Full question stats table */}
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="border-b bg-gray-50 px-6 py-3">
            <h2 className="text-lg font-semibold text-gray-800">Tüm Sorular</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">ID</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Soru</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Konu</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Zorluk</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-600">Cevap</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-600">Doğru%</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {stats.map((q) => (
                  <tr key={q.question_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{q.question_id}</td>
                    <td className="px-4 py-2 max-w-xs truncate">{q.question_text_short}</td>
                    <td className="px-4 py-2">{q.topic_id}</td>
                    <td className="px-4 py-2">{q.difficulty}</td>
                    <td className="px-4 py-2 text-right">{q.total_answers}</td>
                    <td className="px-4 py-2 text-right">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          q.correct_pct < 50
                            ? "bg-red-100 text-red-700"
                            : q.correct_pct < 75
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-green-100 text-green-700"
                        }`}
                      >
                        {q.correct_pct}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </InstructorRouteGuard>
  );
}
