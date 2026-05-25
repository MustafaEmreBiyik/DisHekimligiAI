"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { miniCaseAPI, MiniCaseListItem, MiniCaseDetail } from "@/lib/api";
import { Stethoscope, ArrowLeft, BookOpen, Target, ChevronRight } from "lucide-react";

const difficultyColors: Record<string, string> = {
  easy: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  hard: "bg-red-100 text-red-700",
};

const difficultyLabels: Record<string, string> = {
  easy: "Kolay",
  medium: "Orta",
  hard: "Zor",
};

export default function StudentMiniCasesPage() {
  const { user } = useAuth();
  const [cases, setCases] = useState<MiniCaseListItem[]>([]);
  const [selected, setSelected] = useState<MiniCaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    miniCaseAPI
      .getAll()
      .then(setCases)
      .catch(() => setError("Mini vakalar yüklenemedi."))
      .finally(() => setLoading(false));
  }, [user]);

  const handleSelect = async (miniCaseId: string) => {
    try {
      const detail = await miniCaseAPI.getById(miniCaseId);
      setSelected(detail);
    } catch {
      setError("Vaka detayı yüklenemedi.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (selected) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <button
          onClick={() => setSelected(null)}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-6"
        >
          <ArrowLeft size={18} /> Listeye Dön
        </button>

        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800">{selected.title}</h2>
            <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${difficultyColors[selected.difficulty] || "bg-gray-100"}`}>
              {difficultyLabels[selected.difficulty] || selected.difficulty}
            </span>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-semibold text-blue-800 mb-2 flex items-center gap-2">
              <Stethoscope size={16} /> Klinik Senaryo
            </h3>
            <p className="text-gray-700 leading-relaxed">{selected.clinical_vignette}</p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <Target size={16} /> Anahtar Bulgular
              </h3>
              <ul className="space-y-1">
                {selected.key_findings.map((f, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className="text-blue-500 mt-1">•</span> {f}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <BookOpen size={16} /> Öğrenme Hedefleri
              </h3>
              <ul className="space-y-1">
                {selected.learning_objectives.map((o, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className="text-green-500 mt-1">•</span> {o}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {selected.question_ids.length > 0 && (
            <div className="mt-6 pt-4 border-t">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">İlgili Sorular</h3>
              <div className="flex flex-wrap gap-2">
                {selected.question_ids.map((qid) => (
                  <span
                    key={qid}
                    className="px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-700"
                  >
                    {qid}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-6">
        <Stethoscope size={28} className="text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-800">Mini Vakalar</h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {cases.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <Stethoscope size={48} className="mx-auto mb-4 opacity-30" />
          <p>Henüz mini vaka bulunmuyor.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {cases.map((c) => (
            <button
              key={c.mini_case_id}
              onClick={() => handleSelect(c.mini_case_id)}
              className="w-full bg-white rounded-xl shadow-sm border p-5 hover:border-blue-300 hover:shadow-md transition-all text-left flex items-center justify-between"
            >
              <div>
                <div className="font-semibold text-gray-800 mb-1">{c.title}</div>
                <div className="text-sm text-gray-500 flex gap-3">
                  <span>{c.question_count} soru</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${difficultyColors[c.difficulty] || "bg-gray-100"}`}>
                    {difficultyLabels[c.difficulty] || c.difficulty}
                  </span>
                </div>
              </div>
              <ChevronRight size={18} className="text-gray-400" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
