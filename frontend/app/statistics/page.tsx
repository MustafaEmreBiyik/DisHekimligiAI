"use client";

import React, { useState, useEffect } from "react";
import {
  BarChart2,
  Lightbulb,
  TrendingUp,
  PieChart,
  Target,
  List,
  CheckCircle2,
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
import { userAPI } from "@/lib/api";
import { useRouter } from "next/navigation";

const PIE_COLORS = ["#667eea", "#f093fb", "#4facfe", "#43e97b", "#f6ad55", "#fc8181"];

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
};

export default function StatisticsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [isMounted, setIsMounted] = useState(false);
  const [stats, setStats] = useState<StatsData>(EMPTY_STATS);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      loadStats();
    }
  }, [user]);

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
          data.histogram_data?.length > 0
            ? data.histogram_data
            : EMPTY_STATS.histogram_data,
        recommendation: data.recommendation ?? "",
      });
    } catch (err: any) {
      console.error("Failed to load stats:", err);
      setError("İstatistikler yüklenirken bir hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading) return null;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>
          <BarChart2 size={32} color="#0066cc" />
          Performans İstatistikleri
        </h1>
      </div>

      {error && (
        <div
          style={{
            background: "#fff5f5",
            border: "1px solid #fed7d7",
            color: "#c53030",
            padding: "0.75rem 1rem",
            borderRadius: "8px",
            marginBottom: "1.5rem",
          }}
        >
          ⚠️ {error}
        </div>
      )}

      {/* Overview Metrics Grid */}
      <div className={styles.metricsGrid}>
        <div className={`${styles.metricCard} ${styles.bgBluePurple}`}>
          <p className={styles.metricValue}>
            {isLoading ? "—" : stats.total_score}
          </p>
          <p className={styles.metricLabel}>Toplam Puan</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgPinkRed}`}>
          <p className={styles.metricValue}>
            {isLoading ? "—" : stats.total_actions}
          </p>
          <p className={styles.metricLabel}>Toplam Eylem</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgCyanBlue}`}>
          <p className={styles.metricValue}>
            {isLoading ? "—" : stats.average_score.toFixed(1)}
          </p>
          <p className={styles.metricLabel}>Ortalama Puan/Eylem</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgGreenTeal}`}>
          <p className={styles.metricValue}>
            {isLoading ? "—" : stats.completed_cases}
          </p>
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
            <p>
              İstatistiklerin burada görünmesi için önce bir vakayı tamamlayın.
            </p>
          </div>
        </div>
      ) : null}

      {/* Charts */}
      {isMounted && !isLoading && (
        <>
          <div className={styles.chartsGrid2}>
            {/* Trend Chart */}
            <div className={styles.chartCard}>
              <h3>
                <TrendingUp size={22} color="#667eea" /> Puan Trendi
              </h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={
                      stats.trend_data.length > 0
                        ? stats.trend_data
                        : [{ actionIndex: 0, cumulative: 0 }]
                    }
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="actionIndex" stroke="#a0aec0" />
                    <YAxis stroke="#a0aec0" />
                    <Tooltip
                      contentStyle={{
                        borderRadius: "8px",
                        border: "none",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="cumulative"
                      name="Kümülatif Puan"
                      stroke="#667eea"
                      strokeWidth={4}
                      activeDot={{ r: 8 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Pie Chart */}
            <div className={styles.chartCard}>
              <h3>
                <PieChart size={22} color="#f093fb" /> Eylem Dağılımı
              </h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={
                        stats.pie_data.length > 0
                          ? stats.pie_data
                          : [{ name: "Veri Yok", value: 1 }]
                      }
                      cx="50%"
                      cy="50%"
                      innerRadius={80}
                      outerRadius={110}
                      paddingAngle={5}
                      dataKey="value"
                      label={({
                        name,
                        percent,
                      }: {
                        name?: string;
                        percent?: number;
                      }) =>
                        `${name || ""} ${(((percent || 0) * 100).toFixed(0))}%`
                      }
                      labelLine={false}
                    >
                      {(stats.pie_data.length > 0
                        ? stats.pie_data
                        : [{ name: "Veri Yok", value: 1 }]
                      ).map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={PIE_COLORS[index % PIE_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        borderRadius: "8px",
                        border: "none",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                      }}
                    />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Score Distribution */}
          <div className={styles.chartsGrid1}>
            <div className={styles.chartCard}>
              <h3>
                <Target size={22} color="#4facfe" /> Puan Dağılımı
              </h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={stats.histogram_data}
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      opacity={0.3}
                      vertical={false}
                    />
                    <XAxis dataKey="scoreRange" stroke="#a0aec0" />
                    <YAxis stroke="#a0aec0" />
                    <Tooltip
                      contentStyle={{
                        borderRadius: "8px",
                        border: "none",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                      }}
                    />
                    <Bar
                      dataKey="count"
                      name="Frekans"
                      fill="#4facfe"
                      radius={[6, 6, 0, 0]}
                    />
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
            <h3>
              <List size={22} color="#4a5568" /> Son Eylemler (Son 10 İşlem)
            </h3>
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
                    <td>
                      <strong>{item.case_id}</strong>
                    </td>
                    <td>{item.action}</td>
                    <td>{item.score}</td>
                    <td>
                      <span
                        className={`${styles.tag} ${
                          item.outcome === "success" || item.outcome === "Başarılı"
                            ? styles.tagSuccess
                            : item.outcome === "partial" || item.outcome === "Kısmi"
                            ? styles.tagWarning
                            : styles.tagInfo
                        }`}
                      >
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
            <h3>
              <CheckCircle2 size={22} color="#4a5568" /> Eylem Tipine Göre
              Performans
            </h3>
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
                    <td>
                      <strong>{stat.type}</strong>
                    </td>
                    <td>{stat.usage}</td>
                    <td>{stat.total}</td>
                    <td>
                      <span
                        style={{
                          color:
                            stat.mean >= 9
                              ? "#276749"
                              : stat.mean >= 7
                              ? "#c05621"
                              : "#e53e3e",
                          fontWeight: 700,
                        }}
                      >
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
