"use client";

/**
 * Dashboard Page
 * ==============
 * Protected dashboard with case selection for authenticated students.
 * Now fetches cases dynamically from the API.
 */

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { casesAPI } from "@/lib/api";

interface CaseItem {
  case_id: string;
  name: string | null;
  difficulty: string | null;
  category: string | null;
  patient: {
    age: number | null;
    gender: string | null;
    chief_complaint: string | null;
  } | null;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, logout, isLoading: authLoading } = useAuth();

  // State for cases
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [isLoadingCases, setIsLoadingCases] = useState(true);
  const [error, setError] = useState("");

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  // Fetch cases from API
  useEffect(() => {
    if (user) {
      fetchCases();
    }
  }, [user]);

  const fetchCases = async () => {
    setIsLoadingCases(true);
    setError("");

    try {
      const casesData = await casesAPI.getAllCases();
      setCases(casesData);
    } catch (err: any) {
      console.error("Failed to fetch cases:", err);
      setError("Vakalar yüklenirken bir hata oluştu.");
      // Fallback to static cases if API fails
      setCases([
        {
          case_id: "olp_001",
          name: "Oral Liken Planus",
          difficulty: "Orta",
          category: null,
          patient: {
            age: 45,
            gender: null,
            chief_complaint: "Ağzımda beyaz çizgiler ve acı hissediyorum",
          },
        },
        {
          case_id: "infectious_child_01",
          name: "Primer Herpetik Gingivostomatitis (Pediatrik)",
          difficulty: "Zor",
          category: "INFECTIOUS",
          patient: {
            age: 5,
            gender: "Erkek",
            chief_complaint: "Ebeveyn: 3 gündür yemek yemiyor, sürekli ağlıyor",
          },
        },
      ]);
    } finally {
      setIsLoadingCases(false);
    }
  };

  // Get icon based on category or case_id
  const getCaseIcon = (caseItem: CaseItem): string => {
    const id = caseItem.case_id.toLowerCase();
    const category = caseItem.category?.toLowerCase();

    if (
      id.includes("herpes") ||
      id.includes("infectious") ||
      category === "infectious"
    ) {
      return "🦠";
    } else if (id.includes("perio")) {
      return "🦷";
    } else if (
      id.includes("child") ||
      (caseItem.patient?.age && caseItem.patient.age < 18)
    ) {
      return "👶";
    } else if (id.includes("behcet")) {
      return "🔴";
    } else if (id.includes("syphilis")) {
      return "⚠️";
    } else if (id.includes("olp") || id.includes("liken")) {
      return "🔬";
    }
    return "📋";
  };

  // Get color based on difficulty
  const getCaseColor = (difficulty: string | null): string => {
    if (!difficulty) return "from-gray-500 to-gray-600";

    const d = difficulty.toLowerCase();
    if (d === "kolay" || d === "easy") {
      return "from-green-500 to-green-600";
    } else if (d === "orta" || d === "medium") {
      return "from-blue-500 to-blue-600";
    } else if (d === "zor" || d === "hard" || d === "difficult") {
      return "from-red-500 to-red-600";
    }
    return "from-purple-500 to-purple-600";
  };

  // Get difficulty badge color
  const getDifficultyBadge = (
    difficulty: string | null
  ): { bg: string; text: string } => {
    if (!difficulty) return { bg: "bg-gray-100", text: "text-gray-800" };

    const d = difficulty.toLowerCase();
    if (d === "kolay" || d === "easy") {
      return { bg: "bg-green-100", text: "text-green-800" };
    } else if (d === "orta" || d === "medium") {
      return { bg: "bg-yellow-100", text: "text-yellow-800" };
    } else if (d === "zor" || d === "hard" || d === "difficult") {
      return { bg: "bg-red-100", text: "text-red-800" };
    }
    return { bg: "bg-gray-100", text: "text-gray-800" };
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                🦷 Dental Tutor AI
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-gray-500">Hoş geldin,</p>
                <p className="font-semibold text-gray-900">{user.name}</p>
              </div>
              <button
                onClick={logout}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors text-sm font-medium"
              >
                Çıkış Yap
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Welcome Section */}
        <div className="mb-12">
          <h2 className="text-4xl font-bold text-gray-900 mb-3">
            Hoş geldin, {user.name} 👋
          </h2>
          <p className="text-lg text-gray-600 mb-2">
            Öğrenci ID:{" "}
            <span className="font-mono font-semibold">{user.student_id}</span>
          </p>
          <p className="text-gray-600">
            Aşağıdaki vakalardan birini seçerek eğitiminize başlayabilirsiniz.
          </p>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-6 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* Cases Section */}
        <div className="mb-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">
            📁 Mevcut Vakalar
          </h3>

          {isLoadingCases ? (
            <div className="grid md:grid-cols-2 gap-6">
              {[1, 2].map((i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-100 animate-pulse"
                >
                  <div className="h-2 bg-gray-200"></div>
                  <div className="p-6">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-gray-200 rounded-xl"></div>
                      <div className="flex-1">
                        <div className="h-6 bg-gray-200 rounded w-3/4 mb-2"></div>
                        <div className="h-4 bg-gray-200 rounded w-full mb-4"></div>
                        <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6">
              {cases.map((caseItem) => {
                const badgeColors = getDifficultyBadge(caseItem.difficulty);

                return (
                  <Link
                    key={caseItem.case_id}
                    href={`/chat/${caseItem.case_id}`}
                    className="group bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden border border-gray-100 hover:border-blue-200 transform hover:-translate-y-1"
                  >
                    <div
                      className={`h-2 bg-gradient-to-r ${getCaseColor(
                        caseItem.difficulty
                      )}`}
                    ></div>
                    <div className="p-6">
                      <div className="flex items-start gap-4">
                        <div className="text-5xl">{getCaseIcon(caseItem)}</div>
                        <div className="flex-1">
                          <h4 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                            {caseItem.name || caseItem.case_id}
                          </h4>
                          <p className="text-gray-600 text-sm mb-4">
                            {caseItem.patient?.chief_complaint ||
                              "Hasta bekleme odasında"}
                          </p>
                          <div className="flex items-center gap-3">
                            {caseItem.difficulty && (
                              <span
                                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${badgeColors.bg} ${badgeColors.text}`}
                              >
                                {caseItem.difficulty}
                              </span>
                            )}
                            {caseItem.patient?.age && (
                              <span className="text-sm text-gray-500">
                                👤 {caseItem.patient.age} yaş
                              </span>
                            )}
                            <span className="text-sm text-gray-500">
                              Vaka ID: {caseItem.case_id}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <p className="text-blue-600 font-semibold text-sm group-hover:text-blue-700 flex items-center gap-2">
                          Vakayı Başlat
                          <svg
                            className="w-4 h-4 transform group-hover:translate-x-1 transition-transform"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M13 7l5 5m0 0l-5 5m5-5H6"
                            />
                          </svg>
                        </p>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">
            ⚡ Hızlı Erişim
          </h3>

          <div className="grid md:grid-cols-3 gap-4">
            <Link
              href="/stats"
              className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-all border border-gray-100 hover:border-purple-200"
            >
              <div className="text-3xl mb-3">📊</div>
              <h4 className="font-bold text-gray-900 mb-1">İstatistiklerim</h4>
              <p className="text-sm text-gray-600">
                Performans analizi ve ilerleme
              </p>
            </Link>

            <Link
              href="/cases"
              className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-all border border-gray-100 hover:border-purple-200"
            >
              <div className="text-3xl mb-3">📚</div>
              <h4 className="font-bold text-gray-900 mb-1">Tüm Vakalar</h4>
              <p className="text-sm text-gray-600">Vaka kütüphanesine göz at</p>
            </Link>

            <Link
              href="/profile"
              className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-all border border-gray-100 hover:border-purple-200"
            >
              <div className="text-3xl mb-3">👤</div>
              <h4 className="font-bold text-gray-900 mb-1">Profilim</h4>
              <p className="text-sm text-gray-600">
                Hesap ayarları ve bilgileri
              </p>
            </Link>
          </div>
        </div>

        {/* Info Banner */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-8 rounded-2xl shadow-xl">
          <div className="flex items-start gap-4">
            <div className="text-4xl">💡</div>
            <div className="flex-1">
              <h3 className="text-2xl font-bold mb-3">Nasıl Çalışır?</h3>
              <div className="space-y-2 text-blue-50">
                <p>✓ Bir vaka seçin ve yapay zeka destekli sohbeti başlatın</p>
                <p>✓ Tanı ve tedavi yaklaşımınızı açıklayın</p>
                <p>✓ Gerçek zamanlı geri bildirim alın ve öğrenin</p>
                <p>✓ İlerlemenizi takip edin ve performansınızı geliştirin</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
