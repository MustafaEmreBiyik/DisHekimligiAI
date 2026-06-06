"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Clock, AlertTriangle, Send, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Question {
  id: string;
  question: string;
  options: string[];
  question_type: string;
}

export default function ExamPage() {
  const params = useParams();
  const router = useRouter();
  const scheduleId = params.scheduleId as string;

  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [expiresAt, setExpiresAt] = useState<Date | null>(null);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const submitted = useRef(false);

  const startExam = useCallback(async () => {
    const tok = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const hdrs = { "Content-Type": "application/json", Authorization: `Bearer ${tok}` };
    try {
      const res = await fetch(`${API_BASE}/api/quiz/exam-schedules/${scheduleId}/start`, {
        method: "POST",
        headers: hdrs,
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError((d as Record<string, string>).detail || `Error ${res.status}`);
        return;
      }
      const data = await res.json();
      setAttemptId(data.attempt_id);
      if (data.time_limit_expires_at) {
        setExpiresAt(new Date(data.time_limit_expires_at));
      }
      const qRes = await fetch(`${API_BASE}/api/quiz/questions`, { headers: hdrs });
      if (qRes.ok) {
        const allQ = await qRes.json();
        setQuestions(allQ.slice(0, data.question_count));
      }
    } catch {
      setError("Bağlantı hatası.");
    }
  }, [scheduleId]);

  useEffect(() => {
    startExam();
  }, [startExam]);

  const handleSubmit = async () => {
    if (submitted.current || !attemptId) return;
    submitted.current = true;
    setSubmitting(true);
    const tok = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    try {
      await fetch(`${API_BASE}/api/quiz/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tok}` },
        body: JSON.stringify({ answers }),
      });
    } catch {
      // best effort
    }
    setSubmitting(false);
    setDone(true);
  };

  useEffect(() => {
    if (!expiresAt) return;
    const interval = setInterval(() => {
      const diff = Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000));
      setTimeLeft(diff);
      if (diff <= 0 && !submitted.current) {
        handleSubmit();
      }
    }, 1000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expiresAt]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <AlertTriangle className="mx-auto mb-2 text-red-500" size={32} />
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => router.push("/student/calendar")}
            className="mt-4 text-sm text-blue-600 hover:underline"
          >
            Takvime Dön
          </button>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <Send className="mx-auto mb-2 text-green-600" size={32} />
          <h2 className="text-lg font-bold text-green-800">Sınav Gönderildi</h2>
          <p className="text-sm text-green-700 mt-2">
            Cevaplarınız başarıyla kaydedildi.
          </p>
          <button
            onClick={() => router.push("/student/history")}
            className="mt-4 text-sm text-blue-600 hover:underline"
          >
            Sınav Geçmişi
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      {/* Timer bar */}
      {timeLeft !== null && (
        <div
          className={`sticky top-0 z-10 mb-4 flex items-center justify-between rounded-lg px-4 py-3 shadow ${
            timeLeft < 60 ? "bg-red-100 border border-red-300" : "bg-blue-50 border border-blue-200"
          }`}
        >
          <div className="flex items-center gap-2">
            <Clock size={18} className={timeLeft < 60 ? "text-red-600" : "text-blue-600"} />
            <span className={`font-mono text-lg font-bold ${timeLeft < 60 ? "text-red-700" : "text-blue-700"}`}>
              {formatTime(timeLeft)}
            </span>
          </div>
          <span className="text-xs text-gray-500">
            {questions.length} soru · {Object.keys(answers).length} cevaplanmış
          </span>
        </div>
      )}

      {/* Questions */}
      <div className="space-y-6">
        {questions.map((q, idx) => (
          <div key={q.id} className="bg-white border rounded-xl p-5 shadow-sm">
            <p className="font-medium text-gray-800 mb-3">
              {idx + 1}. {q.question}
            </p>
            {q.options && q.options.length > 0 ? (
              <div className="space-y-2">
                {q.options.map((opt, oi) => (
                  <label
                    key={oi}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition ${
                      answers[q.id] === opt
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`q-${q.id}`}
                      checked={answers[q.id] === opt}
                      onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: opt }))}
                      className="accent-blue-600"
                    />
                    <span className="text-sm">{opt}</span>
                  </label>
                ))}
              </div>
            ) : (
              <textarea
                rows={3}
                value={answers[q.id] || ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                className="w-full border rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-200 focus:outline-none"
                placeholder="Cevabınızı yazın..."
              />
            )}
          </div>
        ))}
      </div>

      {questions.length > 0 && (
        <div className="mt-6 flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-white font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {submitting ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            Sınavı Gönder
          </button>
        </div>
      )}
    </div>
  );
}
