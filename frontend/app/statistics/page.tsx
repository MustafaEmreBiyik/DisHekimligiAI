"use client";

import React, { useState, useEffect } from "react";
import {
  BarChart2,
  Download,
  Lightbulb,
  TrendingUp,
  PieChart,
  Target,
  List,
  CheckCircle2,
  BookOpen,
  AlertTriangle,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPie,
  Pie,
  Cell,
  BarChart,
  Bar,
} from "recharts";
import styles from "./Statistics.module.css";
import { useAuth } from "@/context/AuthContext";
import {
  getApiErrorMessage,
  userAPI,
  quizAPI,
  CompositeScoreData,
  TopicAccuracyData,
  TopicAccuracyItem,
} from "@/lib/api";
import { useRouter } from "next/navigation";

const PIE_COLORS = ["#667eea", "#f093fb", "#4facfe", "#43e97b", "#f6ad55", "#fc8181"];

// ── Composite score helpers ───────────────────────────────────────────────────

const COMPONENT_META = [
  { key: "mcq" as const,        label: "Çoktan Seçmeli",  shortLabel: "ÇSS",  color: "#667eea", bg: "linear-gradient(135deg,#667eea 0%,#764ba2 100%)" },
  { key: "open_ended" as const, label: "Açık Uçlu",       shortLabel: "AUS",  color: "#f093fb", bg: "linear-gradient(135deg,#f093fb 0%,#f5576c 100%)" },
  { key: "case" as const,       label: "Klinik Vaka",     shortLabel: "KVS",  color: "#43e97b", bg: "linear-gradient(135deg,#43e97b 0%,#38f9d7 100%)" },
];

function pctLabel(pct: number | null): string {
  if (pct === null) return "—";
  return `${pct.toFixed(1)}%`;
}

function compositeGrade(pct: number): { label: string; color: string } {
  if (pct >= 90) return { label: "Mükemmel",  color: "#276749" };
  if (pct >= 75) return { label: "İyi",        color: "#2b6cb0" };
  if (pct >= 60) return { label: "Yeterli",    color: "#c05621" };
  return           { label: "Geliştirmeli", color: "#c53030" };
}

// ── Topic accuracy helpers ────────────────────────────────────────────────────

function topicBarColor(item: TopicAccuracyItem): string {
  if (item.pct === null) return "#a0aec0";
  return item.is_weak ? "#fc8181" : "#43e97b";
}

interface TopicTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: TopicAccuracyItem }>;
}

function TopicTooltip({ active, payload }: TopicTooltipProps) {
  if (!active || !payload?.length) return null;
  const t = payload[0].payload;
  return (
    <div style={{
      background: "white",
      border: "1px solid #e2e8f0",
      borderRadius: 10,
      padding: "0.75rem 1rem",
      boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
      fontSize: "0.88rem",
    }}>
      <p style={{ margin: "0 0 0.4rem", fontWeight: 700, color: "#1a202c" }}>{t.topic_label}</p>
      <p style={{ margin: "0 0 0.2rem", color: "#4a5568" }}>Doğruluk: <strong>{pctLabel(t.pct)}</strong></p>
      <p style={{ margin: "0 0 0.2rem", color: "#4a5568" }}>Puan: {t.earned}/{t.max_possible}</p>
      <p style={{ margin: "0 0 0.2rem", color: "#4a5568" }}>Cevaplanan: {t.answered_count} soru</p>
      <p style={{ margin: 0, color: "#4a5568" }}>Tam doğru: {t.correct_count}</p>
      <p style={{
        margin: "0.4rem 0 0",
        fontWeight: 700,
        color: t.is_weak ? "#c53030" : "#276749",
      }}>
        {t.is_weak ? "⚠ Zayıf konu" : "✓ Güçlü konu"}
      </p>
    </div>
  );
}

// ── Existing stats interface ──────────────────────────────────────────────────

interface StatsData {
  total_sessions: number;
  completed_cases: number;
  total_score: number;
  total_actions: number;
  average_score: number;
  action_history: Array<{
    timestamp: string;
    case_id: string;
    action: string;
    score: number;
    outcome: string;
  }>;
  trend_data: Array<{ actionIndex: number; cumulative: number }>;
  action_type_stats: Array<{ type: string; usage: number; total: number; mean: number }>;
  pie_data: Array<{ name: string; value: number }>;
  histogram_data: Array<{ scoreRange: string; count: number }>;
  recommendation: string;
  reasoning_pattern: {
    pattern: string;
    confidence: number;
    evidence?: {
      total_actions?: number;
      history_actions?: number;
      test_actions?: number;
      diagnosis_position?: number;
      deviation_flags_after_diagnosis?: number;
    };
  } | null;
}

const EMPTY_STATS: StatsData = {
  total_sessions: 0,
  completed_cases: 0,
  total_score: 0,
  total_actions: 0,
  average_score: 0,
  action_history: [],
  trend_data: [],
  action_type_stats: [],
  pie_data: [],
  histogram_data: [
    { scoreRange: "0-2 Puan", count: 0 },
    { scoreRange: "3-5 Puan", count: 0 },
    { scoreRange: "6-8 Puan", count: 0 },
    { scoreRange: "9-10 Puan", count: 0 },
  ],
  recommendation: "",
  reasoning_pattern: null,
};

function getReasoningPatternUI(pattern: string) {
  if (pattern === "HYPOTHESIS_DRIVEN_INQUIRY") {
    return { label: "Hypothesis-Driven Inquiry", bg: "#f0fff4", color: "#276749", border: "#9ae6b4" };
  }
  if (pattern === "DATA_DRIVEN_EXPLORATION") {
    return { label: "Data-Driven Exploration", bg: "#fffbea", color: "#975a16", border: "#f6e05e" };
  }
  if (pattern === "FAILED_HYPOTHESIS_REVISION") {
    return { label: "Failed Hypothesis Revision", bg: "#fff5f5", color: "#c53030", border: "#feb2b2" };
  }
  if (pattern === "PREMATURE_DIAGNOSTIC_CLOSURE") {
    return { label: "Premature Diagnostic Closure", bg: "#fff5f5", color: "#c53030", border: "#feb2b2" };
  }
  return { label: pattern, bg: "#edf2f7", color: "#4a5568", border: "#cbd5e0" };
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function StatisticsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [isMounted, setIsMounted] = useState(false);

  // Existing case-simulation stats
  const [stats, setStats] = useState<StatsData>(EMPTY_STATS);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // New quiz score data
  const [compositeScore, setCompositeScore] = useState<CompositeScoreData | null>(null);
  const [topicAccuracy, setTopicAccuracy] = useState<TopicAccuracyData | null>(null);
  const [scoreLoading, setScoreLoading] = useState(true);
  const [scoreError, setScoreError] = useState("");

  useEffect(() => { setIsMounted(true); }, []);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      loadStats();
      loadQuizScores();
    }
  }, [user]);

  // ── Loaders ──────────────────────────────────────────────────────────────

  const loadStats = async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await userAPI.getStats();
      setStats({
        total_sessions: data.total_sessions ?? 0,
        completed_cases: data.completed_cases ?? 0,
        total_score: data.total_score ?? 0,
        total_actions: data.total_actions ?? 0,
        average_score: data.average_score ?? 0,
        action_history: data.action_history ?? [],
        trend_data: data.trend_data ?? [],
        action_type_stats: data.action_type_stats ?? [],
        pie_data: data.pie_data ?? [],
        histogram_data:
          data.histogram_data?.length > 0 ? data.histogram_data : EMPTY_STATS.histogram_data,
        recommendation: data.recommendation ?? "",
        reasoning_pattern: data.reasoning_pattern ?? null,
      });
    } catch (err: unknown) {
      console.error("Failed to load stats:", err);
      setError(getApiErrorMessage(err, "İstatistikler yüklenirken bir hata oluştu."));
    } finally {
      setIsLoading(false);
    }
  };

  const loadQuizScores = async () => {
    setScoreLoading(true);
    setScoreError("");
    try {
      const [scoreData, topicData] = await Promise.all([
        quizAPI.getMyScore(),
        quizAPI.getMyTopicAccuracy(),
      ]);
      setCompositeScore(scoreData);
      setTopicAccuracy(topicData);
    } catch (err: unknown) {
      console.error("Failed to load quiz scores:", err);
      setScoreError(getApiErrorMessage(err, "Quiz puanları yüklenirken bir hata oluştu."));
    } finally {
      setScoreLoading(false);
    }
  };

  if (authLoading) return null;

  // ── Derived display values ────────────────────────────────────────────────

  const hasComposite = compositeScore?.composite_pct !== null && compositeScore?.composite_pct !== undefined;
  const grade = hasComposite ? compositeGrade(compositeScore!.composite_pct as number) : null;
  const weakTopics = topicAccuracy?.topics.filter((t) => t.is_weak) ?? [];

  return (
    <div className={styles.container}>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className={styles.pageHeader} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h1 className={styles.pageTitle}>
          <BarChart2 size={32} color="#0066cc" />
          Performans İstatistikleri
        </h1>
        <button
          onClick={async () => {
            const token = localStorage.getItem("access_token");
            const res = await fetch(
              `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/quiz/my-report?format=pdf`,
              { headers: { Authorization: `Bearer ${token}` } }
            );
            if (!res.ok) return;
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "rapor.pdf";
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition"
        >
          <Download size={16} />
          PDF İndir
        </button>
      </div>

      {/* ── Error banners ─────────────────────────────────────────────────── */}
      {error && (
        <div style={{
          background: "#fff5f5", border: "1px solid #fed7d7", color: "#c53030",
          padding: "0.75rem 1rem", borderRadius: "8px", marginBottom: "1.5rem",
        }}>
          ⚠️ {error}
        </div>
      )}
      {scoreError && (
        <div style={{
          background: "#fff5f5", border: "1px solid #fed7d7", color: "#c53030",
          padding: "0.75rem 1rem", borderRadius: "8px", marginBottom: "1.5rem",
        }}>
          ⚠️ {scoreError}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          COMPOSITE SCORE CARD  (T-2B)
      ══════════════════════════════════════════════════════════════════════ */}
      <div className={styles.chartCard} style={{ marginBottom: "2rem" }}>
        <h3 style={{ marginBottom: "1.25rem" }}>
          <Target size={22} color="#0066cc" /> Genel Kompozit Puan
        </h3>

        {scoreLoading ? (
          <div style={{ textAlign: "center", padding: "2rem", color: "#a0aec0", fontSize: "1rem" }}>
            Yükleniyor…
          </div>
        ) : !compositeScore || compositeScore.composite_pct === null ? (
          /* Cold start */
          <div style={{
            display: "flex", alignItems: "center", gap: "1rem",
            background: "#f7fafc", borderRadius: "10px", padding: "1.5rem",
            color: "#718096",
          }}>
            <BookOpen size={32} color="#a0aec0" />
            <div>
              <p style={{ margin: 0, fontWeight: 600, color: "#4a5568" }}>Henüz Puan Yok</p>
              <p style={{ margin: "0.25rem 0 0", fontSize: "0.9rem" }}>
                Kompozit puanınızın burada görünmesi için bir quiz tamamlayın ve değerlendirme
                sonuçlarının yayımlanmasını bekleyin.
              </p>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem", alignItems: "stretch" }}>
            {/* Big composite number */}
            <div style={{
              flex: "0 0 auto", minWidth: 160,
              background: "linear-gradient(135deg,#667eea 0%,#764ba2 100%)",
              borderRadius: "16px", padding: "1.5rem 2rem",
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              color: "white", boxShadow: "0 8px 24px rgba(102,126,234,0.25)",
            }}>
              <span style={{ fontSize: "3.5rem", fontWeight: 800, lineHeight: 1 }}>
                {(compositeScore.composite_pct as number).toFixed(1)}
              </span>
              <span style={{ fontSize: "1.1rem", fontWeight: 500, opacity: 0.9 }}>%</span>
              {grade && (
                <span style={{
                  marginTop: "0.5rem", fontSize: "0.85rem", fontWeight: 700,
                  background: "rgba(255,255,255,0.2)", borderRadius: "999px",
                  padding: "0.15rem 0.6rem",
                }}>
                  {grade.label}
                </span>
              )}
            </div>

            {/* Three component cards */}
            <div style={{
              flex: "1 1 0", display: "grid",
              gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: "1rem",
            }}>
              {COMPONENT_META.map(({ key, label, bg }) => {
                const comp = compositeScore[key];
                return (
                  <div key={key} style={{
                    borderRadius: "14px", padding: "1rem 1.25rem",
                    background: bg, color: "white",
                    boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
                    display: "flex", flexDirection: "column", gap: "0.4rem",
                  }}>
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, opacity: 0.85, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                      {label}
                    </span>
                    <span style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1 }}>
                      {comp.available ? pctLabel(comp.pct) : "—"}
                    </span>
                    <span style={{ fontSize: "0.78rem", opacity: 0.85 }}>
                      {comp.available
                        ? `${comp.earned} / ${comp.max_possible} puan`
                        : "Henüz veri yok"}
                    </span>
                    <span style={{
                      fontSize: "0.75rem", opacity: 0.75,
                      borderTop: "1px solid rgba(255,255,255,0.3)", paddingTop: "0.35rem", marginTop: "auto",
                    }}>
                      Ağırlık: %{(comp.effective_weight * 100).toFixed(0)}
                      {!compositeScore.all_components_available && " (yeniden dağıtıldı)"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Missing component notice */}
        {!scoreLoading && compositeScore && !compositeScore.all_components_available &&
          compositeScore.composite_pct !== null && (
          <p style={{
            marginTop: "1rem", marginBottom: 0,
            fontSize: "0.82rem", color: "#718096",
            background: "#fffbea", borderRadius: "6px", padding: "0.5rem 0.75rem",
          }}>
            ⓘ Bazı bileşenler henüz tamamlanmadığından ağırlıklar mevcut bileşenlere orantılı olarak
            yeniden dağıtıldı.
          </p>
        )}
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          TOPIC ACCURACY / WEAK TOPIC PANEL  (T-2C)
      ══════════════════════════════════════════════════════════════════════ */}
      <div className={styles.chartCard} style={{ marginBottom: "2rem" }}>
        <h3 style={{ marginBottom: "1.25rem" }}>
          <AlertTriangle size={22} color="#dd6b20" /> Konuya Göre Doğruluk (ÇSS)
        </h3>

        {scoreLoading ? (
          <div style={{ textAlign: "center", padding: "2rem", color: "#a0aec0" }}>Yükleniyor…</div>
        ) : !topicAccuracy?.has_any_data ? (
          <div style={{
            display: "flex", alignItems: "center", gap: "1rem",
            background: "#f7fafc", borderRadius: "10px", padding: "1.5rem",
            color: "#718096",
          }}>
            <BookOpen size={32} color="#a0aec0" />
            <div>
              <p style={{ margin: 0, fontWeight: 600, color: "#4a5568" }}>Henüz Quiz Geçmişi Yok</p>
              <p style={{ margin: "0.25rem 0 0", fontSize: "0.9rem" }}>
                Çoktan seçmeli sorular tamamlandıktan ve değerlendirme yayımlandıktan sonra
                konu bazında doğruluk oranlarınız burada görünecektir.
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Weak topic alert */}
            {weakTopics.length > 0 && (
              <div style={{
                background: "#fff5f5", border: "1px solid #fed7d7", borderRadius: "8px",
                padding: "0.75rem 1rem", marginBottom: "1.25rem",
                display: "flex", alignItems: "flex-start", gap: "0.75rem",
              }}>
                <AlertTriangle size={18} color="#c53030" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <span style={{ fontWeight: 700, color: "#c53030" }}>
                    {weakTopics.length} zayıf konu tespit edildi:&nbsp;
                  </span>
                  <span style={{ color: "#744210" }}>
                    {weakTopics.map((t) => t.topic_label).join(", ")}
                  </span>
                  <span style={{ color: "#718096", fontSize: "0.85rem", display: "block", marginTop: "0.2rem" }}>
                    %60 altı doğruluk zayıf sayılır.
                  </span>
                </div>
              </div>
            )}

            {/* Bar chart */}
            {isMounted && (
              <div style={{ width: "100%", height: Math.max(220, topicAccuracy.topics.length * 52 + 40) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={topicAccuracy.topics}
                    layout="vertical"
                    margin={{ top: 4, right: 48, left: 8, bottom: 4 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" opacity={0.25} horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      tickFormatter={(v: number) => `${v}%`}
                      stroke="#a0aec0"
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="topic_label"
                      width={130}
                      stroke="#a0aec0"
                      tick={{ fontSize: 12, fill: "#4a5568" }}
                    />
                    <Tooltip content={<TopicTooltip />} />
                    {/* 60% threshold reference line rendered as a bar overlay is complex;
                        instead we use coloured bars to communicate weak/strong */}
                    <Bar dataKey="pct" name="Doğruluk" radius={[0, 6, 6, 0]} maxBarSize={32}>
                      {topicAccuracy.topics.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={topicBarColor(entry)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Legend */}
            <div style={{
              display: "flex", gap: "1.5rem", marginTop: "0.75rem",
              fontSize: "0.82rem", color: "#718096",
            }}>
              <span><span style={{ display: "inline-block", width: 12, height: 12, background: "#fc8181", borderRadius: 3, marginRight: 4, verticalAlign: "middle" }} />Zayıf konu (&lt;60%)</span>
              <span><span style={{ display: "inline-block", width: 12, height: 12, background: "#43e97b", borderRadius: 3, marginRight: 4, verticalAlign: "middle" }} />Güçlü konu (≥60%)</span>
            </div>
          </>
        )}
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          EXISTING CONTENT (case simulation stats — unchanged)
      ══════════════════════════════════════════════════════════════════════ */}

      {/* Reasoning Pattern */}
      {!isLoading && stats.reasoning_pattern?.pattern && (
        <div style={{
          background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px",
          padding: "0.9rem 1rem", marginBottom: "1rem",
          display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.75rem",
        }}>
          <span style={{ color: "#4a5568", fontWeight: 700 }}>Reasoning Pattern:</span>
          <span style={{
            background: getReasoningPatternUI(stats.reasoning_pattern.pattern).bg,
            color: getReasoningPatternUI(stats.reasoning_pattern.pattern).color,
            border: `1px solid ${getReasoningPatternUI(stats.reasoning_pattern.pattern).border}`,
            borderRadius: "999px", padding: "0.2rem 0.7rem",
            fontSize: "0.85rem", fontWeight: 700,
          }}>
            {getReasoningPatternUI(stats.reasoning_pattern.pattern).label}
          </span>
          <span style={{ color: "#718096", fontSize: "0.85rem" }}>
            Confidence: {(stats.reasoning_pattern.confidence * 100).toFixed(0)}%
          </span>
        </div>
      )}

      {/* Overview Metrics Grid */}
      <div className={styles.metricsGrid}>
        <div className={`${styles.metricCard} ${styles.bgBluePurple}`}>
          <p className={styles.metricValue}>{isLoading ? "—" : stats.total_score}</p>
          <p className={styles.metricLabel}>Toplam Puan</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgPinkRed}`}>
          <p className={styles.metricValue}>{isLoading ? "—" : stats.total_actions}</p>
          <p className={styles.metricLabel}>Toplam Eylem</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgCyanBlue}`}>
          <p className={styles.metricValue}>{isLoading ? "—" : stats.average_score.toFixed(1)}</p>
          <p className={styles.metricLabel}>Ortalama Puan/Eylem</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgGreenTeal}`}>
          <p className={styles.metricValue}>{isLoading ? "—" : stats.completed_cases}</p>
          <p className={styles.metricLabel}>Tamamlanan Vaka</p>
        </div>
      </div>

      {/* Recommendation / Weakness Detection */}
      {stats.recommendation ? (
        <div className={styles.recommendationBox}>
          <Lightbulb size={28} className={styles.recommendationIcon} />
          <div className={styles.recommendationContent}>
            <h3>Gelişim Önerileri</h3>
            <p>{stats.recommendation}</p>
          </div>
        </div>
      ) : !isLoading && stats.total_actions === 0 ? (
        <div className={styles.recommendationBox}>
          <Lightbulb size={28} className={styles.recommendationIcon} />
          <div className={styles.recommendationContent}>
            <h3>Henüz Veri Yok</h3>
            <p>İstatistiklerin burada görünmesi için önce bir vakayı tamamlayın.</p>
          </div>
        </div>
      ) : null}

      {/* Charts */}
      {isMounted && !isLoading && (
        <>
          <div className={styles.chartsGrid2}>
            {/* Trend Chart */}
            <div className={styles.chartCard}>
              <h3><TrendingUp size={22} color="#667eea" /> Puan Trendi</h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={stats.trend_data.length > 0 ? stats.trend_data : [{ actionIndex: 0, cumulative: 0 }]}
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="actionIndex" stroke="#a0aec0" />
                    <YAxis stroke="#a0aec0" />
                    <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} />
                    <Line type="monotone" dataKey="cumulative" name="Kümülatif Puan" stroke="#667eea" strokeWidth={4} activeDot={{ r: 8 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Pie Chart */}
            <div className={styles.chartCard}>
              <h3><PieChart size={22} color="#f093fb" /> Eylem Dağılımı</h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={stats.pie_data.length > 0 ? stats.pie_data : [{ name: "Veri Yok", value: 1 }]}
                      cx="50%" cy="50%"
                      innerRadius={80} outerRadius={110}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }: { name?: string; percent?: number }) =>
                        `${name || ""} ${(((percent || 0) * 100).toFixed(0))}%`
                      }
                      labelLine={false}
                    >
                      {(stats.pie_data.length > 0 ? stats.pie_data : [{ name: "Veri Yok", value: 1 }]).map(
                        (_, index) => <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      )}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Score Distribution */}
          <div className={styles.chartsGrid1}>
            <div className={styles.chartCard}>
              <h3><Target size={22} color="#4facfe" /> Puan Dağılımı</h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.histogram_data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                    <XAxis dataKey="scoreRange" stroke="#a0aec0" />
                    <YAxis stroke="#a0aec0" />
                    <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} />
                    <Bar dataKey="count" name="Frekans" fill="#4facfe" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Data Tables */}
      <div className={styles.tablesGrid}>
        {/* Recent Actions Table */}
        <div className={styles.tableWrapper}>
          <div className={styles.tableHeader}>
            <h3><List size={22} color="#4a5568" /> Son Eylemler (Son 10 İşlem)</h3>
          </div>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Tarih</th>
                <th>Vaka</th>
                <th>Eylem Tipi</th>
                <th>Puan</th>
                <th>Sonuç</th>
              </tr>
            </thead>
            <tbody>
              {stats.action_history.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", color: "#718096", padding: "1.5rem" }}>
                    Henüz eylem geçmişi yok
                  </td>
                </tr>
              ) : (
                stats.action_history.map((item, idx) => (
                  <tr key={idx}>
                    <td>{item.timestamp}</td>
                    <td><strong>{item.case_id}</strong></td>
                    <td>{item.action}</td>
                    <td>{item.score}</td>
                    <td>
                      <span className={`${styles.tag} ${
                        item.outcome === "success" || item.outcome === "Başarılı" ? styles.tagSuccess
                        : item.outcome === "partial" || item.outcome === "Kısmi" ? styles.tagWarning
                        : styles.tagInfo
                      }`}>
                        {item.outcome}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Action Type Performance */}
        <div className={styles.tableWrapper}>
          <div className={styles.tableHeader}>
            <h3><CheckCircle2 size={22} color="#4a5568" /> Eylem Tipine Göre Performans</h3>
          </div>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Eylem Tipi</th>
                <th>Kullanım Sayısı</th>
                <th>Toplam Puan</th>
                <th>Ortalama Puan</th>
              </tr>
            </thead>
            <tbody>
              {stats.action_type_stats.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", color: "#718096", padding: "1.5rem" }}>
                    Henüz veri yok
                  </td>
                </tr>
              ) : (
                stats.action_type_stats.map((stat, idx) => (
                  <tr key={idx}>
                    <td><strong>{stat.type}</strong></td>
                    <td>{stat.usage}</td>
                    <td>{stat.total}</td>
                    <td>
                      <span style={{
                        color: stat.mean >= 9 ? "#276749" : stat.mean >= 7 ? "#c05621" : "#e53e3e",
                        fontWeight: 700,
                      }}>
                        {stat.mean.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
