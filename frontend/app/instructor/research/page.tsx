"use client";

import { useState, useEffect } from "react";
import {
  instructorAPI,
  OutcomeCorrelationResponse,
  CorrelationStudentPoint,
} from "@/lib/api";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { ArrowLeft, BarChart2 } from "lucide-react";
import Link from "next/link";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Label,
} from "recharts";

// ── Scatter Plot ───────────────────────────────────────────────────────────────

function CorrelationScatterPlot({ students }: { students: CorrelationStudentPoint[] }) {
  const paired = students.filter(
    (s) => s.quiz_pct !== null && s.case_pct !== null
  );

  const data = paired.map((s) => ({
    x: s.quiz_pct!,
    y: s.case_pct!,
    name: s.display_name,
  }));

  return (
    <div className="bg-white rounded-xl border p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-800 mb-1">Dağılım Grafiği</h3>
      <p className="text-xs text-gray-400 mb-4">
        Her nokta bir öğrenci — X: Quiz/Teori %, Y: Vaka Simülasyonu %
      </p>
      {data.length < 2 ? (
        <div className="h-40 flex items-center justify-center text-xs text-gray-400">
          Yeterli eşleştirilmiş veri yok (en az 2 öğrenci gerekli)
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
            >
              <Label value="Quiz / Teori %" offset={-10} position="insideBottom" fontSize={11} fill="#6b7280" />
            </XAxis>
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
            >
              <Label value="Vaka %" angle={-90} position="insideLeft" fontSize={11} fill="#6b7280" />
            </YAxis>
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-white border rounded-lg shadow p-2 text-xs">
                    <p className="font-semibold text-gray-800">{d.name}</p>
                    <p className="text-gray-600">Quiz: {d.x.toFixed(1)}%</p>
                    <p className="text-gray-600">Vaka: {d.y.toFixed(1)}%</p>
                  </div>
                );
              }}
            />
            <ReferenceLine x={70} stroke="#e5e7eb" strokeDasharray="4 2" />
            <ReferenceLine y={70} stroke="#e5e7eb" strokeDasharray="4 2" />
            <Scatter data={data} fill="#6366f1" opacity={0.8} r={5} />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

// ── Student Table ──────────────────────────────────────────────────────────────

function StudentCorrelationTable({ students }: { students: CorrelationStudentPoint[] }) {
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left font-semibold text-gray-700">Öğrenci</th>
            <th className="px-4 py-3 text-center font-semibold text-gray-700">Quiz / Teori %</th>
            <th className="px-4 py-3 text-center font-semibold text-gray-700">Vaka %</th>
            <th className="px-4 py-3 text-center font-semibold text-gray-700">Durum</th>
          </tr>
        </thead>
        <tbody>
          {students.map((s) => {
            const bothAvail = s.quiz_pct !== null && s.case_pct !== null;
            return (
              <tr key={s.user_id} className="border-b hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">
                  <Link
                    href={`/instructor/students/${s.user_id}`}
                    className="hover:text-blue-600 hover:underline"
                  >
                    {s.display_name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-center">
                  {s.quiz_pct !== null ? (
                    <span
                      className={`font-semibold ${s.quiz_pct >= 70 ? "text-green-600" : s.quiz_pct >= 40 ? "text-yellow-600" : "text-red-600"}`}
                    >
                      {s.quiz_pct.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-gray-400 text-xs">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  {s.case_pct !== null ? (
                    <span
                      className={`font-semibold ${s.case_pct >= 70 ? "text-green-600" : s.case_pct >= 40 ? "text-yellow-600" : "text-red-600"}`}
                    >
                      {s.case_pct.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-gray-400 text-xs">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      bothAvail
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {bothAvail ? "Eşleştirildi" : "Eksik veri"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

function ResearchPageContent() {
  const [data, setData] = useState<OutcomeCorrelationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    instructorAPI
      .getOutcomeCorrelation()
      .then(setData)
      .catch(() => setError("Veri yüklenemedi."))
      .finally(() => setLoading(false));
  }, []);

  const rColor =
    data?.pearson_r === null
      ? "text-gray-500"
      : data!.pearson_r! >= 0.7
      ? "text-green-600"
      : data!.pearson_r! >= 0.4
      ? "text-yellow-600"
      : "text-red-600";

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link
            href="/instructor/dashboard"
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <ArrowLeft size={18} className="text-gray-600" />
          </Link>
          <div className="flex items-center gap-2">
            <BarChart2 size={22} className="text-blue-600" />
            <div>
              <h1 className="text-lg font-bold text-gray-900">Quiz ↔ Vaka Çıktı Korelasyonu</h1>
              <p className="text-xs text-gray-500">
                Yapı geçerliliği kanıtı · Pearson r · Yayınlanabilir
              </p>
            </div>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {data && (
          <>
            {/* Correlation summary */}
            <div className="grid grid-cols-3 gap-3 mb-5">
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className={`text-3xl font-bold ${rColor}`}>
                  {data.pearson_r !== null ? data.pearson_r.toFixed(2) : "—"}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">Pearson r</p>
              </div>
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-blue-600">{data.n_paired}</p>
                <p className="text-xs text-gray-500 mt-0.5">Eşleştirilmiş Öğrenci</p>
              </div>
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-gray-700">{data.students.length}</p>
                <p className="text-xs text-gray-500 mt-0.5">Toplam Öğrenci</p>
              </div>
            </div>

            {/* Interpretation */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-5">
              <p className="text-sm text-blue-800">{data.interpretation}</p>
            </div>

            {/* Scatter plot */}
            <div className="mb-5">
              <CorrelationScatterPlot students={data.students} />
            </div>

            {/* Student table */}
            <StudentCorrelationTable students={data.students} />

            <p className="text-[10px] text-gray-400 text-center mt-4">
              Hesaplanma: {new Date(data.computed_at).toLocaleString("tr-TR")}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default function ResearchPage() {
  return (
    <InstructorRouteGuard>
      <ResearchPageContent />
    </InstructorRouteGuard>
  );
}
