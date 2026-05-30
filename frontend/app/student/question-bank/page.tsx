"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search, X, ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
  quizAPI,
  QuestionBankEntry,
  QuestionBankFilters,
} from "@/lib/api";

// ── Constants ─────────────────────────────────────────────────────────────────

const DIFFICULTY_OPTIONS = [
  { label: "Tümü", value: "" },
  { label: "Kolay", value: "easy" },
  { label: "Orta", value: "medium" },
  { label: "Zor", value: "hard" },
];

const TYPE_OPTIONS = [
  { label: "Tümü", value: "" },
  { label: "Çoktan Seçmeli", value: "MCQ" },
  { label: "Açık Uçlu", value: "OPEN_ENDED" },
];

const BLOOM_OPTIONS = [
  { label: "Tümü", value: "" },
  { label: "Hatırlama", value: "remember" },
  { label: "Anlama", value: "understand" },
  { label: "Uygulama", value: "apply" },
  { label: "Analiz", value: "analyze" },
];

const DIFFICULTY_LABEL: Record<string, string> = {
  easy: "Kolay",
  medium: "Orta",
  hard: "Zor",
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  hard: "bg-red-100 text-red-800",
};

const BLOOM_LABEL: Record<string, string> = {
  remember: "Hatırlama",
  understand: "Anlama",
  apply: "Uygulama",
  analyze: "Analiz",
};

// ── Filter pill helper ────────────────────────────────────────────────────────

function PillGroup({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-2 py-1 rounded-full text-xs font-medium transition-colors ${
            value === opt.value
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// ── Main content ──────────────────────────────────────────────────────────────

function QuestionBankContent() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Filter state — initialised from URL so filters survive reload
  const [searchText, setSearchText] = useState(
    () => searchParams.get("search") ?? "",
  );
  const [debouncedSearch, setDebouncedSearch] = useState(
    () => searchParams.get("search") ?? "",
  );
  const [selectedTopic, setSelectedTopic] = useState(
    () => searchParams.get("topic") ?? "",
  );
  const [selectedDifficulty, setSelectedDifficulty] = useState(
    () => searchParams.get("difficulty") ?? "",
  );
  const [selectedType, setSelectedType] = useState(
    () => searchParams.get("question_type") ?? "",
  );
  const [selectedBloom, setSelectedBloom] = useState(
    () => searchParams.get("bloom_level") ?? "",
  );

  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [topics, setTopics] = useState<string[]>(["Tümü"]);
  const [questions, setQuestions] = useState<QuestionBankEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Auth guard
  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  // Load topic list once
  useEffect(() => {
    if (user) {
      quizAPI.getTopics().then(setTopics).catch(() => {});
    }
  }, [user]);

  // Debounce search input 300 ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchText), 300);
    return () => clearTimeout(t);
  }, [searchText]);

  // Sync all committed filters to URL (no extra history entries)
  useEffect(() => {
    const sp = new URLSearchParams();
    if (debouncedSearch) sp.set("search", debouncedSearch);
    if (selectedTopic) sp.set("topic", selectedTopic);
    if (selectedDifficulty) sp.set("difficulty", selectedDifficulty);
    if (selectedType) sp.set("question_type", selectedType);
    if (selectedBloom) sp.set("bloom_level", selectedBloom);
    const qs = sp.toString();
    router.replace(
      qs ? `/student/question-bank?${qs}` : "/student/question-bank",
      { scroll: false },
    );
  }, [
    debouncedSearch,
    selectedTopic,
    selectedDifficulty,
    selectedType,
    selectedBloom,
    router,
  ]);

  // Fetch questions whenever committed filters change
  const fetchQuestions = useCallback(async () => {
    if (!user) return;
    setIsLoading(true);
    try {
      const filters: QuestionBankFilters = {};
      if (selectedTopic) filters.topic = selectedTopic;
      if (selectedDifficulty) filters.difficulty = selectedDifficulty;
      if (selectedType) filters.question_type = selectedType;
      if (selectedBloom) filters.bloom_level = selectedBloom;
      if (debouncedSearch) filters.search = debouncedSearch;
      const data = await quizAPI.getQuestionBank(filters);
      setQuestions(data);
    } catch (err) {
      console.error("Failed to load question bank:", err);
      setQuestions([]);
    } finally {
      setIsLoading(false);
    }
  }, [
    user,
    selectedTopic,
    selectedDifficulty,
    selectedType,
    selectedBloom,
    debouncedSearch,
  ]);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  // Active filter badges (shown in header strip)
  type Badge = { key: string; label: string; clear: () => void };
  const badges: Badge[] = [
    ...(selectedTopic
      ? [{ key: "topic", label: selectedTopic, clear: () => setSelectedTopic("") }]
      : []),
    ...(selectedDifficulty
      ? [
          {
            key: "difficulty",
            label: DIFFICULTY_LABEL[selectedDifficulty] ?? selectedDifficulty,
            clear: () => setSelectedDifficulty(""),
          },
        ]
      : []),
    ...(selectedType
      ? [
          {
            key: "type",
            label: selectedType === "MCQ" ? "Çoktan Seçmeli" : "Açık Uçlu",
            clear: () => setSelectedType(""),
          },
        ]
      : []),
    ...(selectedBloom
      ? [
          {
            key: "bloom",
            label: BLOOM_LABEL[selectedBloom] ?? selectedBloom,
            clear: () => setSelectedBloom(""),
          },
        ]
      : []),
    ...(searchText
      ? [
          {
            key: "search",
            label: `"${searchText}"`,
            clear: () => setSearchText(""),
          },
        ]
      : []),
  ];

  const hasActiveFilters = badges.length > 0;

  const clearAll = () => {
    setSearchText("");
    setSelectedTopic("");
    setSelectedDifficulty("");
    setSelectedType("");
    setSelectedBloom("");
  };

  const toggleExpand = (id: string) =>
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  if (authLoading) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Page header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">Soru Bankası</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Tüm soruları inceleyin ve deneme geçmişinizi takip edin
        </p>
      </div>

      <div className="flex gap-0">
        {/* ── LEFT SIDEBAR ──────────────────────────────────────────────── */}
        <aside className="w-72 shrink-0 border-r border-gray-200 bg-white min-h-[calc(100vh-73px)]">
          <div className="p-5">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Filtreler
            </h2>

            {/* Search */}
            <div className="mb-5">
              <label className="text-xs font-medium text-gray-500 mb-1 block">
                Arama
              </label>
              <div className="relative">
                <Search
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                />
                <input
                  type="text"
                  placeholder="Soru metni ara…"
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  className="w-full pl-8 pr-7 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {searchText && (
                  <button
                    onClick={() => setSearchText("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>

            {/* Topic */}
            <div className="mb-5">
              <label className="text-xs font-medium text-gray-500 mb-2 block">
                Konu
              </label>
              <div className="flex flex-wrap gap-1">
                {topics.map((t) => (
                  <button
                    key={t}
                    onClick={() =>
                      setSelectedTopic(t === "Tümü" ? "" : t)
                    }
                    className={`px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                      (t === "Tümü" && !selectedTopic) ||
                      t === selectedTopic
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div className="mb-5">
              <label className="text-xs font-medium text-gray-500 mb-2 block">
                Zorluk
              </label>
              <PillGroup
                options={DIFFICULTY_OPTIONS}
                value={selectedDifficulty}
                onChange={setSelectedDifficulty}
              />
            </div>

            {/* Question type */}
            <div className="mb-5">
              <label className="text-xs font-medium text-gray-500 mb-2 block">
                Soru Tipi
              </label>
              <PillGroup
                options={TYPE_OPTIONS}
                value={selectedType}
                onChange={setSelectedType}
              />
            </div>

            {/* Bloom level */}
            <div className="mb-5">
              <label className="text-xs font-medium text-gray-500 mb-2 block">
                Bloom Seviyesi
              </label>
              <PillGroup
                options={BLOOM_OPTIONS}
                value={selectedBloom}
                onChange={setSelectedBloom}
              />
            </div>

            {/* Clear all */}
            {hasActiveFilters && (
              <button
                onClick={clearAll}
                className="w-full mt-1 py-2 text-sm text-red-600 hover:text-red-800 font-medium border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
              >
                Filtreleri Temizle
              </button>
            )}
          </div>
        </aside>

        {/* ── MAIN AREA ─────────────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 p-6">
          {/* Result count + active badges */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="text-sm text-gray-500">
              {isLoading
                ? "Yükleniyor…"
                : `${questions.length} soru gösteriliyor`}
            </span>
            {badges.map((b) => (
              <span
                key={b.key}
                className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full"
              >
                {b.label}
                <button
                  onClick={b.clear}
                  className="hover:text-blue-900 ml-0.5"
                >
                  <X size={11} />
                </button>
              </span>
            ))}
          </div>

          {/* Question list */}
          {isLoading ? (
            <div className="flex justify-center items-center py-24">
              <div className="w-8 h-8 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
            </div>
          ) : questions.length === 0 ? (
            <div className="text-center py-24 text-gray-400">
              <BookOpen size={48} className="mx-auto mb-3 opacity-30" />
              <p className="text-lg font-medium text-gray-500">
                Soru bulunamadı
              </p>
              <p className="text-sm mt-1">
                Filtreleri değiştirerek tekrar deneyin.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {questions.map((q, idx) => {
                const isExpanded = expandedIds.has(q.question_id);
                const { attempted, last_score } = q.attempt_summary;

                let dotClass = "bg-gray-300";
                let dotTitle = "Henüz denenmedi";
                if (attempted) {
                  const pct =
                    last_score !== null && q.max_score > 0
                      ? (last_score / q.max_score) * 100
                      : 0;
                  if (pct >= 70) {
                    dotClass = "bg-green-500";
                    dotTitle = `Denendi — %${Math.round(pct)}`;
                  } else {
                    dotClass = "bg-yellow-500";
                    dotTitle = `Denendi — %${Math.round(pct)}`;
                  }
                }

                return (
                  <div
                    key={q.question_id}
                    className="bg-white rounded-xl border border-gray-200 overflow-hidden"
                  >
                    {/* Card header — click to expand */}
                    <button
                      className="w-full text-left p-4 flex items-start gap-3 hover:bg-gray-50 transition-colors"
                      onClick={() => toggleExpand(q.question_id)}
                    >
                      {/* Attempt indicator dot */}
                      <span
                        className={`mt-1.5 w-2.5 h-2.5 rounded-full shrink-0 ${dotClass}`}
                        title={dotTitle}
                      />

                      <div className="flex-1 min-w-0">
                        <p
                          className={`text-sm text-gray-900 leading-relaxed ${
                            !isExpanded ? "line-clamp-2" : ""
                          }`}
                        >
                          <span className="text-gray-400 mr-1">
                            {idx + 1}.
                          </span>
                          {q.question_text}
                        </p>

                        {/* Metadata badges */}
                        <div className="flex flex-wrap gap-1 mt-2">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
                            {q.topic_id}
                          </span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full ${
                              DIFFICULTY_COLOR[q.difficulty] ??
                              "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {DIFFICULTY_LABEL[q.difficulty] ?? q.difficulty}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
                            {q.question_type === "MCQ"
                              ? "Çoktan Seçmeli"
                              : "Açık Uçlu"}
                          </span>
                          {q.bloom_level && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-teal-100 text-teal-700">
                              {BLOOM_LABEL[q.bloom_level] ?? q.bloom_level}
                            </span>
                          )}
                        </div>
                      </div>

                      {isExpanded ? (
                        <ChevronUp
                          size={16}
                          className="shrink-0 text-gray-400 mt-1"
                        />
                      ) : (
                        <ChevronDown
                          size={16}
                          className="shrink-0 text-gray-400 mt-1"
                        />
                      )}
                    </button>

                    {/* Expanded body */}
                    {isExpanded && (
                      <div className="px-4 pb-4 ml-9 border-t border-gray-100 pt-3">
                        {q.question_type === "MCQ" && q.options_json ? (
                          <ul className="space-y-1.5">
                            {q.options_json.map((opt, i) => (
                              <li
                                key={i}
                                className="flex items-center gap-2 text-sm text-gray-700"
                              >
                                <span className="w-5 h-5 rounded-full bg-gray-100 flex items-center justify-center text-xs font-semibold shrink-0 text-gray-500">
                                  {String.fromCharCode(65 + i)}
                                </span>
                                {opt}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-gray-500 italic">
                            Açık uçlu soru — yanıtınızı test modunda yazabilirsiniz.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// Suspense boundary required by Next.js 15 for useSearchParams
export default function QuestionBankPage() {
  return (
    <Suspense>
      <QuestionBankContent />
    </Suspense>
  );
}
