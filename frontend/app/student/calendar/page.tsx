"use client";

import { useEffect, useState } from "react";
import { Calendar, Clock, Play, Loader2 } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ExamScheduleItem {
  id: number;
  title: string;
  question_ids: number[];
  opens_at: string;
  closes_at: string;
  time_limit_minutes: number | null;
  is_active: boolean;
}

export default function StudentCalendarPage() {
  const [exams, setExams] = useState<ExamScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    fetch(`${API_BASE}/api/quiz/exam-schedules/upcoming?days=30`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setExams(data as ExamScheduleItem[]))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const now = new Date();

  const isOpen = (exam: ExamScheduleItem) => {
    const opens = new Date(exam.opens_at);
    const closes = new Date(exam.closes_at);
    return now >= opens && now <= closes;
  };

  const isFuture = (exam: ExamScheduleItem) => {
    return new Date(exam.opens_at) > now;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <Loader2 size={32} className="animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-6">
        <Calendar size={28} className="text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-800">Sınav Takvimi</h1>
      </div>

      {exams.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Calendar size={48} className="mx-auto mb-3 text-gray-300" />
          <p>Yaklaşan sınav bulunmuyor.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {exams.map((exam) => {
            const open = isOpen(exam);
            const future = isFuture(exam);
            const opens = new Date(exam.opens_at);
            const closes = new Date(exam.closes_at);

            return (
              <div
                key={exam.id}
                className={`border rounded-xl p-5 transition ${
                  open
                    ? "border-green-300 bg-green-50"
                    : future
                    ? "border-blue-200 bg-blue-50"
                    : "border-gray-200 bg-white"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-semibold text-gray-800">{exam.title}</h3>
                    <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <Calendar size={14} />
                        {opens.toLocaleDateString("tr-TR")} {opens.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}
                        {" — "}
                        {closes.toLocaleDateString("tr-TR")} {closes.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      {exam.time_limit_minutes && (
                        <span className="flex items-center gap-1">
                          <Clock size={14} />
                          {exam.time_limit_minutes} dk süre
                        </span>
                      )}
                      <span className="text-xs text-gray-500">
                        {exam.question_ids.length} soru
                      </span>
                    </div>

                    {future && (
                      <p className="mt-2 text-xs text-blue-600 font-medium">
                        Açılışa {Math.ceil((opens.getTime() - now.getTime()) / (1000 * 60 * 60))} saat kaldı
                      </p>
                    )}
                  </div>

                  {open && (
                    <Link
                      href={`/student/exam/${exam.id}`}
                      className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition whitespace-nowrap"
                    >
                      <Play size={16} />
                      Başla
                    </Link>
                  )}
                  {future && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700">
                      Yakında
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
