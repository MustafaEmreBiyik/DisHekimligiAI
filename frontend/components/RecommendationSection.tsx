import Link from "next/link";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import type { RecommendationResponse, TopFeature } from "@/lib/api";

interface RecommendationSectionProps {
  data: RecommendationResponse | null;
  isLoading: boolean;
}

const difficultyLabelMap: Record<string, string> = {
  beginner: "Başlangıç",
  intermediate: "Orta",
  advanced: "İleri",
  kolay: "Kolay",
  orta: "Orta",
  zor: "Zor",
};

function getDifficultyLabel(value: string): string {
  const normalized = value.trim().toLowerCase();
  return difficultyLabelMap[normalized] ?? value;
}

function getDifficultyBadgeClass(value: string): string {
  const normalized = value.trim().toLowerCase();

  if (normalized === "beginner" || normalized === "kolay") {
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }

  if (normalized === "intermediate" || normalized === "orta") {
    return "bg-amber-100 text-amber-700 border-amber-200";
  }

  if (normalized === "advanced" || normalized === "zor") {
    return "bg-rose-100 text-rose-700 border-rose-200";
  }

  return "bg-slate-100 text-slate-700 border-slate-200";
}

const FEATURE_LABELS: Record<string, string> = {
  avg_score_pct: "Ortalama Başarı",
  bkt_mastery_avg: "BKT Hakimiyet",
  irt_difficulty_b: "IRT Zorluk (b)",
  n_sessions: "Oturum Sayısı",
  mastery_gap: "Hakimiyet Açığı",
  n_critical_safety_violations: "Güvenlik İhlali",
  n_weak_competency_overlaps: "Zayıf Yetkinlik",
  difficulty_ordinal: "Zorluk Derecesi",
  case_avg_score_pct: "Vaka Ort. Başarı",
  is_completed: "Tamamlandı",
  is_in_progress: "Devam Ediyor",
};

function InlineTopFeatures({ features }: { features: TopFeature[] }) {
  if (!features || features.length === 0) return null;
  const maxC = Math.max(...features.map((f) => f.contribution), 1e-9);
  return (
    <div className="mt-3 space-y-2 rounded-lg border border-slate-100 bg-slate-50 p-3">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Öne Çıkan Faktörler</p>
      {features.map((f, i) => {
        const pct = Math.round((f.contribution / maxC) * 100);
        return (
          <div key={i}>
            <div className="flex items-center justify-between gap-1 mb-0.5">
              <div className="flex items-center gap-1 min-w-0">
                {f.direction === "up" ? (
                  <ArrowUpRight size={12} className="shrink-0 text-emerald-500" />
                ) : (
                  <ArrowDownRight size={12} className="shrink-0 text-rose-500" />
                )}
                <span className="truncate text-xs text-slate-600">
                  {FEATURE_LABELS[f.name] ?? f.name.replace(/_/g, " ")}
                </span>
              </div>
            </div>
            <div className="h-1 w-full rounded-full bg-slate-200">
              <div
                className={`h-1 rounded-full ${f.direction === "up" ? "bg-emerald-400" : "bg-rose-400"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function RecommendationSection({
  data,
  isLoading,
}: RecommendationSectionProps) {
  if (isLoading) {
    return (
      <section className="mb-10">
        <div className="mb-5">
          <h3 className="text-2xl font-bold text-slate-900">
            Sana Özel Vaka Önerileri
          </h3>
          <p className="text-sm text-slate-600 mt-1">Öneriler hazırlanıyor...</p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1, 2].map((item) => (
            <div
              key={item}
              className="rounded-2xl border border-slate-200 bg-white p-5 animate-pulse"
            >
              <div className="h-5 bg-slate-200 rounded w-2/3 mb-3" />
              <div className="h-4 bg-slate-200 rounded w-5/6 mb-2" />
              <div className="h-4 bg-slate-200 rounded w-4/6 mb-4" />
              <div className="h-8 bg-slate-200 rounded w-1/3" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (!data || data.recommendations.length === 0) {
    return null;
  }

  return (
    <section className="mb-10">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-2xl font-bold text-slate-900">
            Sana Özel Vaka Önerileri
          </h3>
          <p className="text-sm text-slate-600 mt-1">
            Klinik performansına göre önceliklendirilmiş en uygun vakalar
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
            <span>Algoritma:</span>
            <span className="text-slate-800">{data.meta.algorithm_version}</span>
          </div>
          <Link
            href="/student/recommendations"
            className="inline-flex items-center gap-1 text-xs font-semibold text-cyan-600 hover:text-cyan-800 transition-colors"
          >
            Tümünü Gör →
          </Link>
        </div>
      </div>

      {data.meta.cold_start && (
        <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          Başlangıç profili uygulandı: önce temel vakalarla ilerlemeni öneriyoruz.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data.recommendations.map((item, index) => (
          <article
            key={item.case_id}
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Öneri #{index + 1}
                </p>
                <h4 className="text-lg font-bold text-slate-900 mt-1">{item.title}</h4>
              </div>
              <span
                className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${getDifficultyBadgeClass(
                  item.difficulty,
                )}`}
              >
                {getDifficultyLabel(item.difficulty)}
              </span>
            </div>

            <p className="text-sm text-slate-600 mb-4 min-h-10">{item.reason_text}</p>

            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="inline-flex rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-700">
                Öncelik: {item.priority_score}
              </span>
              <span className="inline-flex rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700">
                Süre: ~{item.estimated_duration_minutes} dk
              </span>
              {item.competency_tags.slice(0, 2).map((tag) => (
                <span
                  key={`${item.case_id}-${tag}`}
                  className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                >
                  {tag}
                </span>
              ))}
            </div>

            {item.top_features && item.top_features.length > 0 && (
              <InlineTopFeatures features={item.top_features} />
            )}

            <div className="mt-4 flex items-center gap-3">
              <Link
                href={`/chat/${item.case_id}`}
                className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:from-cyan-700 hover:to-blue-700"
              >
                Vakayı Aç
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
