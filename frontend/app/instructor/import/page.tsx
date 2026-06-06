"use client";

import { useState, useRef } from "react";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { Upload, FileUp, CheckCircle, XCircle, AlertTriangle, Loader2 } from "lucide-react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PreviewItem {
  question_id: string;
  question_type: string;
  question_text: string;
  topic_id: string;
  difficulty: string;
  status: string;
}

interface ImportResult {
  added: number;
  updated: number;
  skipped: number;
  errors: string[];
  preview: PreviewItem[];
}

const statusBadge: Record<string, { color: string; label: string }> = {
  added: { color: "bg-green-100 text-green-700", label: "Eklendi" },
  updated: { color: "bg-blue-100 text-blue-700", label: "Güncellendi" },
  skipped: { color: "bg-yellow-100 text-yellow-700", label: "Atlandı" },
  error: { color: "bg-red-100 text-red-700", label: "Hata" },
};

export default function InstructorImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [upsert, setUpsert] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState("");
  const [isDryRun, setIsDryRun] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    setFile(selected);
    setResult(null);
    setError("");
  };

  const handleImport = async (dryRun: boolean) => {
    if (!file) return;
    setLoading(true);
    setError("");
    setIsDryRun(dryRun);

    const formData = new FormData();
    formData.append("file", file);

    const token = localStorage.getItem("access_token");
    const params = new URLSearchParams();
    if (upsert) params.set("upsert", "true");
    if (dryRun) params.set("dry_run", "true");

    try {
      const res = await fetch(
        `${API_URL}/api/quiz/instructor/import?${params.toString()}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || `HTTP ${res.status}`);
        return;
      }
      const data: ImportResult = await res.json();
      setResult(data);
    } catch {
      setError("Bağlantı hatası.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <InstructorRouteGuard>
      <div className="max-w-5xl mx-auto p-6">
        <div className="flex items-center gap-3 mb-6">
          <Upload size={28} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-800">Soru İçe Aktarma</h1>
          <Link
            href="/instructor/questions"
            className="ml-auto text-sm text-blue-600 hover:underline"
          >
            Soru Bankasına Dön
          </Link>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                JSON veya CSV Dosyası Seçin
              </label>
              <div
                className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 transition"
                onClick={() => inputRef.current?.click()}
              >
                <FileUp size={36} className="mx-auto mb-3 text-gray-400" />
                {file ? (
                  <p className="text-sm font-medium text-gray-800">{file.name}</p>
                ) : (
                  <p className="text-sm text-gray-500">
                    Dosya seçmek için tıklayın (.json veya .csv)
                  </p>
                )}
                <input
                  ref={inputRef}
                  type="file"
                  accept=".json,.csv"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={upsert}
                onChange={(e) => setUpsert(e.target.checked)}
                className="rounded border-gray-300"
              />
              Mevcut soruları güncelle (upsert)
            </label>

            <div className="flex gap-3">
              <button
                onClick={() => handleImport(true)}
                disabled={!file || loading}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {loading && isDryRun ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <AlertTriangle size={16} />
                )}
                Önizleme (Dry Run)
              </button>
              <button
                onClick={() => handleImport(false)}
                disabled={!file || loading}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {loading && !isDryRun ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Upload size={16} />
                )}
                İçe Aktar
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-sm text-red-700">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                <CheckCircle size={20} className="mx-auto mb-1 text-green-600" />
                <div className="text-2xl font-bold text-green-700">{result.added}</div>
                <div className="text-xs text-green-600">Eklendi</div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                <CheckCircle size={20} className="mx-auto mb-1 text-blue-600" />
                <div className="text-2xl font-bold text-blue-700">{result.updated}</div>
                <div className="text-xs text-blue-600">Güncellendi</div>
              </div>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                <AlertTriangle size={20} className="mx-auto mb-1 text-yellow-600" />
                <div className="text-2xl font-bold text-yellow-700">{result.skipped}</div>
                <div className="text-xs text-yellow-600">Atlandı</div>
              </div>
            </div>

            {result.errors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-red-800 mb-2 flex items-center gap-2">
                  <XCircle size={16} /> Hatalar ({result.errors.length})
                </h3>
                <ul className="text-xs text-red-700 space-y-1 max-h-40 overflow-y-auto">
                  {result.errors.map((e, i) => (
                    <li key={i}>- {e}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.preview.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">ID</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Tip</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Soru</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Konu</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Zorluk</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Durum</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {result.preview.map((item, i) => {
                      const badge = statusBadge[item.status] || statusBadge.error;
                      return (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-mono text-xs">{item.question_id}</td>
                          <td className="px-4 py-2">{item.question_type}</td>
                          <td className="px-4 py-2 max-w-xs truncate">{item.question_text}</td>
                          <td className="px-4 py-2">{item.topic_id}</td>
                          <td className="px-4 py-2">{item.difficulty}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
                              {badge.label}
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
        )}
      </div>
    </InstructorRouteGuard>
  );
}
