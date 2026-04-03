"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { adminAPI, AdminCaseItem } from "@/lib/api";
import AdminRouteGuard from "@/components/admin/AdminRouteGuard";

type DifficultyLevel = "beginner" | "intermediate" | "advanced";

const DIFFICULTY_OPTIONS: DifficultyLevel[] = [
  "beginner",
  "intermediate",
  "advanced",
];

function formatDate(dateText: string | null): string {
  if (!dateText) {
    return "-";
  }

  const date = new Date(dateText);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function difficultyLabel(difficulty: DifficultyLevel): string {
  if (difficulty === "beginner") {
    return "Başlangıç";
  }
  if (difficulty === "intermediate") {
    return "Orta";
  }
  return "İleri";
}

function difficultyClass(difficulty: DifficultyLevel): string {
  if (difficulty === "beginner") {
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }
  if (difficulty === "intermediate") {
    return "bg-amber-100 text-amber-700 border-amber-200";
  }
  return "bg-rose-100 text-rose-700 border-rose-200";
}

export default function AdminCasesPage() {
  const [cases, setCases] = useState<AdminCaseItem[]>([]);
  const [isLoadingCases, setIsLoadingCases] = useState(true);
  const [showCasesTable, setShowCasesTable] = useState(true);

  const [publishCase, setPublishCase] = useState<AdminCaseItem | null>(null);
  const [changeNotes, setChangeNotes] = useState("");
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishSuccessMessage, setPublishSuccessMessage] = useState("");
  const [publishErrorMessage, setPublishErrorMessage] = useState("");

  const [editCase, setEditCase] = useState<AdminCaseItem | null>(null);
  const [editDifficulty, setEditDifficulty] = useState<DifficultyLevel>("beginner");
  const [editIsActive, setEditIsActive] = useState(true);
  const [isUpdatingCase, setIsUpdatingCase] = useState(false);
  const [editErrorMessage, setEditErrorMessage] = useState("");

  const loadCases = useCallback(async () => {
    setIsLoadingCases(true);

    try {
      const response = await adminAPI.getCases();
      setCases(response.cases);
      setShowCasesTable(true);
    } catch {
      setCases([]);
      setShowCasesTable(false);
    } finally {
      setIsLoadingCases(false);
    }
  }, []);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const sortedCases = useMemo(
    () => [...cases].sort((a, b) => a.title.localeCompare(b.title, "tr")),
    [cases],
  );

  const handleActiveToggle = async (item: AdminCaseItem) => {
    const nextValue = !item.is_active;

    try {
      const updated = await adminAPI.updateCase(item.case_id, {
        is_active: nextValue,
      });

      setCases((prev) =>
        prev.map((row) => (row.case_id === item.case_id ? updated : row)),
      );
    } catch {
      // Sessiz fail: toggle hatasında tabloyu bozma.
    }
  };

  const openPublishModal = (item: AdminCaseItem) => {
    setPublishCase(item);
    setChangeNotes("");
    setPublishErrorMessage("");
    setPublishSuccessMessage("");
  };

  const closePublishModal = () => {
    setPublishCase(null);
    setChangeNotes("");
    setPublishErrorMessage("");
    setPublishSuccessMessage("");
  };

  const handlePublish = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!publishCase || !changeNotes.trim()) {
      return;
    }

    setIsPublishing(true);
    setPublishErrorMessage("");
    setPublishSuccessMessage("");

    try {
      const response = await adminAPI.publishCase(publishCase.case_id, {
        change_notes: changeNotes.trim(),
      });

      setPublishSuccessMessage(
        `Yayınlama başarılı. Yeni sürüm: v${response.published_version}`,
      );

      await loadCases();
    } catch {
      setPublishErrorMessage("Yayınlama işlemi başarısız.");
    } finally {
      setIsPublishing(false);
    }
  };

  const openEditModal = (item: AdminCaseItem) => {
    setEditCase(item);
    setEditDifficulty(item.difficulty);
    setEditIsActive(item.is_active);
    setEditErrorMessage("");
  };

  const closeEditModal = () => {
    setEditCase(null);
    setEditErrorMessage("");
  };

  const handleEditCase = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!editCase) {
      return;
    }

    setIsUpdatingCase(true);
    setEditErrorMessage("");

    try {
      const updated = await adminAPI.updateCase(editCase.case_id, {
        difficulty: editDifficulty,
        is_active: editIsActive,
      });

      setCases((prev) =>
        prev.map((item) => (item.case_id === editCase.case_id ? updated : item)),
      );
      closeEditModal();
    } catch {
      setEditErrorMessage("Vaka güncellenemedi.");
    } finally {
      setIsUpdatingCase(false);
    }
  };

  return (
    <AdminRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">
          <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/admin/dashboard"
                className="inline-flex rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Panele Dön
              </Link>
              <h1 className="text-2xl font-bold text-slate-900">Vaka Kataloğu</h1>
            </div>
          </header>

          {isLoadingCases && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 text-slate-600">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
                <span className="text-sm font-medium">Vakalar yükleniyor...</span>
              </div>
            </section>
          )}

          {!isLoadingCases && showCasesTable && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Vaka Listesi</h2>

              <div className="overflow-x-auto">
                <table className="min-w-full border-separate border-spacing-y-2">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                      <th className="px-3 py-2">Başlık</th>
                      <th className="px-3 py-2">Kategori</th>
                      <th className="px-3 py-2">Zorluk</th>
                      <th className="px-3 py-2">Aktif</th>
                      <th className="px-3 py-2">Yayın Sürümü</th>
                      <th className="px-3 py-2">Son Yayınlama</th>
                      <th className="px-3 py-2">Yayınla</th>
                      <th className="px-3 py-2">Düzenle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedCases.map((item) => (
                      <tr key={item.case_id} className="bg-slate-50 text-sm text-slate-800">
                        <td className="px-3 py-2">
                          <p className="font-medium">{item.title}</p>
                          <p className="text-xs text-slate-500">{item.case_id}</p>
                        </td>
                        <td className="px-3 py-2">{item.category}</td>
                        <td className="px-3 py-2">
                          <span
                            className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${difficultyClass(
                              item.difficulty,
                            )}`}
                          >
                            {difficultyLabel(item.difficulty)}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700">
                            <input
                              type="checkbox"
                              checked={item.is_active}
                              onChange={() => handleActiveToggle(item)}
                              className="h-4 w-4 rounded border-slate-300"
                            />
                            {item.is_active ? "Aktif" : "Pasif"}
                          </label>
                        </td>
                        <td className="px-3 py-2">v{item.published_version}</td>
                        <td className="px-3 py-2">{formatDate(item.last_published_at)}</td>
                        <td className="px-3 py-2">
                          <button
                            type="button"
                            onClick={() => openPublishModal(item)}
                            className="inline-flex rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
                          >
                            Yayınla
                          </button>
                        </td>
                        <td className="px-3 py-2">
                          <button
                            type="button"
                            onClick={() => openEditModal(item)}
                            className="inline-flex rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
                          >
                            Düzenle
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      </div>

      {publishCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">Vaka Yayınla</h3>
              <button
                type="button"
                onClick={closePublishModal}
                className="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Kapat
              </button>
            </div>

            <p className="mb-3 text-sm text-slate-700">
              <span className="font-semibold">Vaka:</span> {publishCase.title}
            </p>

            <form className="space-y-4" onSubmit={handlePublish}>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="change-notes">
                  Değişiklik Notu
                </label>
                <textarea
                  id="change-notes"
                  rows={4}
                  value={changeNotes}
                  onChange={(event) => setChangeNotes(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                  placeholder="Bu sürümde neler değişti?"
                />
              </div>

              {publishSuccessMessage && (
                <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  {publishSuccessMessage}
                </p>
              )}

              {publishErrorMessage && (
                <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {publishErrorMessage}
                </p>
              )}

              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={isPublishing || !changeNotes.trim()}
                  className="inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isPublishing ? "Yayınlanıyor..." : "Yayınla"}
                </button>
                <button
                  type="button"
                  onClick={closePublishModal}
                  className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Vazgeç
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">Vaka Düzenle</h3>
              <button
                type="button"
                onClick={closeEditModal}
                className="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Kapat
              </button>
            </div>

            <form className="space-y-4" onSubmit={handleEditCase}>
              <p className="text-sm text-slate-700">
                <span className="font-semibold">Vaka:</span> {editCase.title} ({editCase.case_id})
              </p>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="difficulty">
                  Zorluk Seviyesi
                </label>
                <select
                  id="difficulty"
                  value={editDifficulty}
                  onChange={(event) => setEditDifficulty(event.target.value as DifficultyLevel)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                >
                  {DIFFICULTY_OPTIONS.map((difficulty) => (
                    <option key={difficulty} value={difficulty}>
                      {difficultyLabel(difficulty)}
                    </option>
                  ))}
                </select>
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-700" htmlFor="is-active">
                <input
                  id="is-active"
                  type="checkbox"
                  checked={editIsActive}
                  onChange={(event) => setEditIsActive(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300"
                />
                Aktif olarak işaretle
              </label>

              {editErrorMessage && <p className="text-sm font-medium text-rose-700">{editErrorMessage}</p>}

              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={isUpdatingCase}
                  className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isUpdatingCase ? "Kaydediliyor..." : "Kaydet"}
                </button>
                <button
                  type="button"
                  onClick={closeEditModal}
                  className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Vazgeç
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AdminRouteGuard>
  );
}
