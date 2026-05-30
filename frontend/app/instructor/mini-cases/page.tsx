"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { miniCaseAPI, MiniCaseListItem } from "@/lib/api";
import { Stethoscope } from "lucide-react";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";

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

export default function InstructorMiniCasesPage() {
  const { user } = useAuth();
  const [cases, setCases] = useState<MiniCaseListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    miniCaseAPI
      .getAll()
      .then(setCases)
      .finally(() => setLoading(false));
  }, [user]);

  return (
    <InstructorRouteGuard>
      <div className="max-w-5xl mx-auto p-6">
        <div className="flex items-center gap-3 mb-6">
          <Stethoscope size={28} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-800">Mini Vakalar</h1>
          <span className="text-sm text-gray-500 ml-auto">{cases.length} vaka</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center min-h-[40vh]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : cases.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <p>Henüz mini vaka bulunmuyor.</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">ID</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Başlık</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Zorluk</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Konular</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Soru</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {cases.map((c) => (
                  <tr key={c.mini_case_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.mini_case_id}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{c.title}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${difficultyColors[c.difficulty] || "bg-gray-100"}`}>
                        {difficultyLabels[c.difficulty] || c.difficulty}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {c.linked_topic_ids.join(", ")}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">{c.question_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </InstructorRouteGuard>
  );
}
