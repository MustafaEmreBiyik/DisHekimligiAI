"use client";

import { useEffect, useState } from "react";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { Calendar, Plus, Loader2, Clock } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ExamScheduleItem {
  id: number;
  title: string;
  question_ids: number[];
  opens_at: string;
  closes_at: string;
  time_limit_minutes: number | null;
  created_by: string;
  is_active: boolean;
}

export default function InstructorExamSchedulesPage() {
  const [schedules, setSchedules] = useState<ExamScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [questionIds, setQuestionIds] = useState("");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [timeLimit, setTimeLimit] = useState("");
  const [creating, setCreating] = useState(false);

  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  const loadSchedules = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/quiz/instructor/exam-schedules`, { headers });
      if (res.ok) setSchedules(await res.json());
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    loadSchedules();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    const ids = questionIds.split(",").map((s) => parseInt(s.trim())).filter((n) => !isNaN(n));
    const body = {
      title,
      question_ids: ids,
      opens_at: new Date(opensAt).toISOString(),
      closes_at: new Date(closesAt).toISOString(),
      time_limit_minutes: timeLimit ? parseInt(timeLimit) : null,
    };
    try {
      const res = await fetch(`${API_BASE}/api/quiz/instructor/exam-schedules`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setShowForm(false);
        setTitle("");
        setQuestionIds("");
        setOpensAt("");
        setClosesAt("");
        setTimeLimit("");
        await loadSchedules();
      }
    } catch {}
    setCreating(false);
  };

  return (
    <InstructorRouteGuard>
      <div className="max-w-5xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Calendar size={28} className="text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-800">Sınav Takvimi</h1>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition"
          >
            <Plus size={16} />
            Yeni Sınav
          </button>
        </div>

        {showForm && (
          <div className="bg-white rounded-xl shadow-sm border p-6 mb-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Başlık</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Ara Sınav 1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Soru ID&apos;leri (virgülle ayırın)
              </label>
              <input
                value={questionIds}
                onChange={(e) => setQuestionIds(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="1, 2, 3, 4, 5"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Açılış</label>
                <input
                  type="datetime-local"
                  value={opensAt}
                  onChange={(e) => setOpensAt(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Kapanış</label>
                <input
                  type="datetime-local"
                  value={closesAt}
                  onChange={(e) => setClosesAt(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Süre Limiti (dakika, opsiyonel)
              </label>
              <input
                type="number"
                value={timeLimit}
                onChange={(e) => setTimeLimit(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Boş bırakılırsa süre sınırı yok"
              />
            </div>
            <button
              onClick={handleCreate}
              disabled={!title || !questionIds || !opensAt || !closesAt || creating}
              className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 transition"
            >
              {creating && <Loader2 size={16} className="animate-spin" />}
              Oluştur
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 size={32} className="animate-spin text-blue-600" />
          </div>
        ) : schedules.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Calendar size={48} className="mx-auto mb-3 text-gray-300" />
            <p>Henüz sınav oluşturulmamış.</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Başlık</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Açılış</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Kapanış</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-600">Soru</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-600">Süre</th>
                  <th className="text-center px-4 py-2 font-medium text-gray-600">Durum</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {schedules.map((s) => {
                  const now = new Date();
                  const opens = new Date(s.opens_at);
                  const closes = new Date(s.closes_at);
                  const isOpen = now >= opens && now <= closes && s.is_active;
                  const isPast = now > closes;

                  return (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium">{s.title}</td>
                      <td className="px-4 py-3 text-xs">
                        {opens.toLocaleDateString("tr-TR")} {opens.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {closes.toLocaleDateString("tr-TR")} {closes.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}
                      </td>
                      <td className="px-4 py-3 text-right">{s.question_ids.length}</td>
                      <td className="px-4 py-3 text-right">
                        {s.time_limit_minutes ? (
                          <span className="inline-flex items-center gap-1">
                            <Clock size={12} /> {s.time_limit_minutes} dk
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            isOpen
                              ? "bg-green-100 text-green-700"
                              : isPast
                              ? "bg-gray-100 text-gray-500"
                              : "bg-blue-100 text-blue-700"
                          }`}
                        >
                          {isOpen ? "Açık" : isPast ? "Kapandı" : "Bekliyor"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </InstructorRouteGuard>
  );
}
