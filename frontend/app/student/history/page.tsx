"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { quizAPI, AttemptListItem, QuizSubmitResponse } from "@/lib/api";
import { History, ChevronRight, ArrowLeft, CheckCircle, Clock, XCircle } from "lucide-react";

export default function StudentHistoryPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [attempts, setAttempts] = useState<AttemptListItem[]>([]);
  const [selectedAttempt, setSelectedAttempt] = useState<QuizSubmitResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    quizAPI
      .getMyAttempts()
      .then(setAttempts)
      .catch(() => setError("Geçmiş yüklenemedi."))
      .finally(() => setLoading(false));
  }, [user]);

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
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (selectedAttempt) {
    return (
      <div className="max-w-4xl mx-auto p-6">
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
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-6">
        <History size={28} className="text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-800">Sınav Geçmişi</h1>
      </div>

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
