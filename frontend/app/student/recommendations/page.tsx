"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import {
  recommendationsAPI,
  type RecommendationResponse,
  type RecommendationItem,
  type TopFeature,
} from "@/lib/api";
import {
  Sparkles,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  ArrowUpRight,
  ArrowDownRight,
  AlertCircle,
  Info,
  ExternalLink,
  Clock,
  Target,
  Camera,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Feature name → Turkish label map
// ---------------------------------------------------------------------------
const FEATURE_LABELS: Record<string, string> = {
  avg_score_pct: "Ortalama Başarı Puanı",
  n_sessions: "Tamamlanan Oturum Sayısı",
  bkt_mastery_avg: "Ortalama BKT Hakimiyet",
  bkt_mastery_min: "En Düşük BKT Hakimiyet",
  bkt_mastery_max: "En Yüksek BKT Hakimiyet",
  irt_difficulty_b: "IRT Zorluk Parametresi (b)",
  irt_discrimination_a: "IRT Ayırt Edicilik (a)",
  n_completed_cases: "Tamamlanan Vaka Sayısı",
  n_attempted_cases: "Denenen Vaka Sayısı",
  is_cold_start: "Yeni Kullanıcı Profili",
  mastery_gap: "Hakimiyet Açığı",
  is_completed: "Vaka Daha Önce Tamamlandı",
  is_in_progress: "Vaka Devam Ediyor",
  avg_session_score: "Oturum Puan Ortalaması",
  n_critical_safety_violations: "Güvenlik İhlali Sayısı",
  n_weak_competency_overlaps: "Zayıf Yetkinlik Örtüşmesi",
  weak_competency_overlap_count: "Zayıf Yetkinlik Örtüşme Sayısı",
  difficulty_ordinal: "Zorluk Derecesi",
  case_avg_score_pct: "Vakadaki Ortalama Başarı",
  historical_n_unique_users_attempted: "Vakayı Deneyen Öğrenci Sayısı",
  case_n_attempts: "Vaka Deneme Sayısı",
  n_prerequisite_competencies: "Ön Koşul Yetkinlik Sayısı",
  n_learning_objectives: "Öğrenme Hedefi Sayısı",
  n_mapped_questions: "Eşlenen Soru Sayısı",
  days_since_last_attempt: "Son Denemeden Geçen Gün",
  score_trend: "Puan Trendi",
  image_finding_match_rate_30d: "Görsel Bulgu Eşleşme Oranı (30g)",
  image_unlock_rate: "Görsel Açma Oranı",
  visual_complexity_score: "Görsel Karmaşıklık Skoru",
};

function getFeatureLabel(name: string): string {
  return FEATURE_LABELS[name] ?? name.replace(/_/g, " ");
}

// ---------------------------------------------------------------------------
// Difficulty helpers
// ---------------------------------------------------------------------------
const DIFFICULTY_LABELS: Record<string, string> = {
  beginner: "Başlangıç",
  intermediate: "Orta",
  advanced: "İleri",
  kolay: "Kolay",
  orta: "Orta",
  zor: "Zor",
};

const DIFFICULTY_CLASSES: Record<string, string> = {
  beginner: "bg-emerald-100 text-emerald-700 border-emerald-200",
  kolay: "bg-emerald-100 text-emerald-700 border-emerald-200",
  intermediate: "bg-amber-100 text-amber-700 border-amber-200",
  orta: "bg-amber-100 text-amber-700 border-amber-200",
  advanced: "bg-rose-100 text-rose-700 border-rose-200",
  zor: "bg-rose-100 text-rose-700 border-rose-200",
};

function getDifficultyLabel(v: string): string {
  return DIFFICULTY_LABELS[v.trim().toLowerCase()] ?? v;
}

function getDifficultyClass(v: string): string {
  return (
    DIFFICULTY_CLASSES[v.trim().toLowerCase()] ??
    "bg-slate-100 text-slate-700 border-slate-200"
  );
}

// ---------------------------------------------------------------------------
// Algorithm badge
// ---------------------------------------------------------------------------
function AlgorithmBadge({ version }: { version: string }) {
  const isV2 = version.includes("v2");
  const isColdStart = version.includes("coldstart");
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
        isColdStart
          ? "bg-blue-100 text-blue-700"
          : isV2
          ? "bg-violet-100 text-violet-700"
          : "bg-slate-100 text-slate-600"
      }`}
    >
      <Sparkles size={12} />
      {isColdStart ? "Adaptif · Başlangıç" : isV2 ? "Adaptif · XGBoost" : "Kural Tabanlı"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// SHAP / top-features panel
// ---------------------------------------------------------------------------
function TopFeaturesPanel({ features }: { features: TopFeature[] }) {
  if (!features || features.length === 0) return null;

  const maxContrib = Math.max(...features.map((f) => f.contribution), 1e-9);

  return (
    <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Öneri Gerekçesi · Öne Çıkan Faktörler
      </p>
      <div className="space-y-3">
        {features.map((feat, i) => {
          const pct = Math.round((feat.contribution / maxContrib) * 100);
          const isUp = feat.direction === "up";
          return (
            <div key={i}>
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  {isUp ? (
                    <ArrowUpRight size={14} className="shrink-0 text-emerald-500" />
                  ) : (
                    <ArrowDownRight size={14} className="shrink-0 text-rose-500" />
                  )}
                  <span className="truncate text-xs text-slate-700">
                    {getFeatureLabel(feat.name)}
                  </span>
                </div>
                <span className="shrink-0 text-xs font-semibold text-slate-500">
                  {(feat.contribution * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-200">
                <div
                  className={`h-1.5 rounded-full transition-all ${
                    isUp ? "bg-emerald-400" : "bg-rose-400"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Bu faktörler, modelin bu vakayı öne çıkarmasında en fazla etkili olan özelliklerdir.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recommendation card
// ---------------------------------------------------------------------------
function RecommendationCard({
  item,
  index,
}: {
  item: RecommendationItem;
  index: number;
}) {
  const [showFeatures, setShowFeatures] = useState(false);
  const hasFeatures = item.top_features && item.top_features.length > 0;

  const reasonCodeLabels: Record<string, string> = {
    weak_competency: "Zayıf Yetkinlik",
    not_attempted: "Henüz Başlanmamış",
    cold_start: "Başlangıç Önerisi",
    difficulty_match: "Uygun Zorluk",
    high_match: "Yüksek Uyum",
    exploration: "Keşif",
    completed: "Tamamlandı",
    visual_skill_gap: "Görsel Bulgu Odağı",
  };

  const reasonBadgeClass: Record<string, string> = {
    weak_competency: "bg-rose-50 text-rose-600",
    not_attempted: "bg-cyan-50 text-cyan-700",
    cold_start: "bg-blue-50 text-blue-700",
    difficulty_match: "bg-violet-50 text-violet-700",
    high_match: "bg-emerald-50 text-emerald-700",
    exploration: "bg-amber-50 text-amber-700",
    completed: "bg-slate-100 text-slate-500",
    visual_skill_gap: "bg-orange-50 text-orange-700",
  };

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              #{index + 1}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                reasonBadgeClass[item.reason_code] ?? "bg-slate-100 text-slate-500"
              }`}
            >
              {item.reason_code === "visual_skill_gap" && <Camera size={11} />}
              {reasonCodeLabels[item.reason_code] ?? item.reason_code}
            </span>
          </div>
          <h4 className="text-base font-bold text-slate-900 leading-snug">{item.title}</h4>
        </div>
        <span
          className={`shrink-0 inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${getDifficultyClass(
            item.difficulty
          )}`}
        >
          {getDifficultyLabel(item.difficulty)}
        </span>
      </div>

      {/* Reason text */}
      <p className="text-sm text-slate-600 mb-4 leading-relaxed">{item.reason_text}</p>

      {/* Meta chips */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1 rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-700">
          <Target size={11} />
          {item.priority_score} puan
        </span>
        <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700">
          <Clock size={11} />
          ~{item.estimated_duration_minutes} dk
        </span>
        {item.competency_tags.slice(0, 2).map((tag) => (
          <span
            key={tag}
            className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600"
          >
            {tag}
          </span>
        ))}
        {item.competency_tags.length > 2 && (
          <span className="text-xs text-slate-400">+{item.competency_tags.length - 2}</span>
        )}
      </div>

      {/* SHAP explainability toggle */}
      {hasFeatures && (
        <button
          onClick={() => setShowFeatures((v) => !v)}
          className="mb-4 flex items-center gap-1.5 text-xs font-semibold text-violet-600 hover:text-violet-800 transition-colors"
        >
          {showFeatures ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {showFeatures ? "Faktörleri Gizle" : "Neden Önerildi?"}
        </button>
      )}

      {showFeatures && hasFeatures && (
        <TopFeaturesPanel features={item.top_features!} />
      )}

      {/* CTA */}
      <Link
        href={`/chat/${item.case_id}`}
        className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:from-cyan-700 hover:to-blue-700"
      >
        Vakayı Aç
        <ExternalLink size={14} />
      </Link>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------
function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {[1, 2, 3, 4].map((n) => (
        <div
          key={n}
          className="rounded-2xl border border-slate-200 bg-white p-5 animate-pulse"
        >
          <div className="flex justify-between mb-3">
            <div className="h-5 bg-slate-200 rounded w-2/3" />
            <div className="h-5 bg-slate-200 rounded w-16" />
          </div>
          <div className="h-4 bg-slate-200 rounded w-full mb-2" />
          <div className="h-4 bg-slate-200 rounded w-4/5 mb-4" />
          <div className="flex gap-2 mb-4">
            <div className="h-6 bg-slate-200 rounded-full w-20" />
            <div className="h-6 bg-slate-200 rounded-full w-16" />
          </div>
          <div className="h-9 bg-slate-200 rounded-lg w-28" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function RecommendationsPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const result = await recommendationsAPI.getMyRecommendations();
      setData(result);
    } catch {
      setError("Öneriler yüklenirken bir hata oluştu. Lütfen tekrar deneyin.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (!user) {
      router.push("/login");
      return;
    }
    load();
  }, [user, router, load]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Page header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Sparkles size={28} className="text-violet-600" />
            <h1 className="text-2xl font-bold text-slate-900">Akıllı Vaka Önerileri</h1>
          </div>
          <p className="text-sm text-slate-500 pl-10">
            Klinik performansına ve öğrenme profiline göre kişiselleştirilmiş vakalar
          </p>
        </div>

        <button
          onClick={() => load(true)}
          disabled={loading || refreshing}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:shadow disabled:opacity-50"
        >
          <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
          Yenile
        </button>
      </div>

      {/* Algorithm + timestamp strip */}
      {data && !loading && (
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <AlgorithmBadge version={data.meta.algorithm_version} />
          <span className="text-xs text-slate-400">
            {new Date(data.meta.generated_at).toLocaleString("tr-TR", {
              day: "2-digit",
              month: "long",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          <span className="text-xs text-slate-400">·</span>
          <span className="text-xs text-slate-400">
            {data.recommendations.length} öneri
          </span>
        </div>
      )}

      {/* Cold-start banner */}
      {data?.meta.cold_start && !loading && (
        <div className="mb-6 flex gap-3 rounded-xl border border-blue-200 bg-blue-50 px-5 py-4">
          <Info size={18} className="mt-0.5 shrink-0 text-blue-500" />
          <div>
            <p className="text-sm font-semibold text-blue-800 mb-0.5">
              Başlangıç profili aktif
            </p>
            <p className="text-sm text-blue-700">
              Henüz yeterli veri bulunmadığından önce temel vakalar önerildi. Daha fazla vaka
              tamamladıkça öneriler kişisel performansına göre daha da hassaslaşacak.
            </p>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && <LoadingSkeleton />}

      {/* Error */}
      {!loading && error && (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <AlertCircle size={44} className="text-rose-400" />
          <p className="text-slate-600">{error}</p>
          <button
            onClick={() => load()}
            className="rounded-lg bg-rose-600 px-5 py-2 text-sm font-semibold text-white hover:bg-rose-700"
          >
            Tekrar Dene
          </button>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && data?.recommendations.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <Sparkles size={44} className="text-slate-300" />
          <p className="text-slate-500">Şu an gösterilecek öneri bulunmuyor.</p>
          <p className="text-sm text-slate-400">
            Birkaç vaka tamamladıktan sonra kişiselleştirilmiş öneriler görünecek.
          </p>
        </div>
      )}

      {/* Recommendation grid */}
      {!loading && !error && data && data.recommendations.length > 0 && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data.recommendations.map((item, i) => (
              <RecommendationCard key={item.case_id} item={item} index={i} />
            ))}
          </div>

          {/* Explainability footer note — only shown when ML model is active */}
          {data.recommendations.some((r) => r.top_features && r.top_features.length > 0) && (
            <p className="mt-8 text-center text-xs text-slate-400">
              &ldquo;Neden Önerildi?&rdquo; panelleri, XGBoost modelinin her vaka için ürettiği
              SHAP (SHapley Additive exPlanations) değerlerine dayanmaktadır.
            </p>
          )}
        </>
      )}
    </div>
  );
}
