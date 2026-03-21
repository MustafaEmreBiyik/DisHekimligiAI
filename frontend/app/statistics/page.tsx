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
  CheckCircle2
} from "lucide-react";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart as RechartsPie, Pie, Cell, 
  BarChart, Bar, Legend
} from "recharts";
import styles from "./Statistics.module.css";

// ==================== MOCK DATA ====================
// Mimicking database `get_student_detailed_history`
const mockStats = {
  totalScore: 485,
  totalActions: 54,
  averageScore: 8.9,
  completedCases: 12
};

const mockRecommendation = "Klinik muayene ve radyografik analizlerde oldukça başarılısınız (Ort. Puan > 9). Ancak geçmiş medikal öykü alma adımını sıkça unuttuğunuz veya eksik bıraktığınız görülüyor. Bir sonraki vakanızda ilk olarak hastanın sistemik hastalıklarını sorgulamaya odaklanın.";

const mockActionHistory = [
  { id: 1, date: "2025-12-10 14:23", case: "Oral Liken Planus", action: "Radyografik İnceleme", score: 10, outcome: "Başarılı" },
  { id: 2, date: "2025-12-10 13:45", case: "Kronik Periodontitis", action: "Tedavi Planlaması", score: 8, outcome: "Kısmi" },
  { id: 3, date: "2025-12-09 16:10", case: "Primer Herpes", action: "Anamnez Alma", score: 5, outcome: "Eksik" },
  { id: 4, date: "2025-12-09 11:30", case: "Gömülü 20 Yaş", action: "Klinik Muayene", score: 10, outcome: "Başarılı" },
  { id: 5, date: "2025-12-08 15:20", case: "Oral Liken Planus", action: "Reçete Yazma", score: 9, outcome: "Başarılı" },
  { id: 6, date: "2025-12-08 14:00", case: "Kök Kanal Tedavisi", action: "Röntgen İstemi", score: 10, outcome: "Başarılı" },
  { id: 7, date: "2025-12-07 09:15", case: "Apikal Apse", action: "Tedavi Planlaması", score: 6, outcome: "Kısmi" },
  { id: 8, date: "2025-12-06 13:40", case: "Ortodontik Anomaliler", action: "Anamnez Alma", score: 7, outcome: "Kısmi" },
  { id: 9, date: "2025-12-05 10:20", case: "Diş Taşı Temizliği", action: "Klinik Muayene", score: 10, outcome: "Başarılı" },
  { id: 10, date: "2025-12-04 16:50", case: "İmplant Planlaması", action: "Radyografik İnceleme", score: 10, outcome: "Başarılı" },
];

const mockTrendData = [
  { actionIndex: 1, cumulative: 50 },
  { actionIndex: 5, cumulative: 120 },
  { actionIndex: 10, cumulative: 210 },
  { actionIndex: 20, cumulative: 295 },
  { actionIndex: 30, cumulative: 340 },
  { actionIndex: 40, cumulative: 410 },
  { actionIndex: 54, cumulative: 485 },
];

const mockPieData = [
  { name: "Anamnez Alma", value: 15 },
  { name: "Klinik Muayene", value: 20 },
  { name: "Radyografik", value: 10 },
  { name: "Tedavi Planı", value: 9 },
];

const mockHistogramData = [
  { scoreRange: "0-2 Puan", count: 2 },
  { scoreRange: "3-5 Puan", count: 8 },
  { scoreRange: "6-8 Puan", count: 18 },
  { scoreRange: "9-10 Puan", count: 26 },
];

const mockActionStats = [
  { type: "Klinik Muayene", usage: 20, total: 190, mean: 9.5 },
  { type: "Anamnez Alma", usage: 15, total: 110, mean: 7.3 },
  { type: "Radyografik İnceleme", usage: 10, total: 95, mean: 9.5 },
  { type: "Tedavi Planlaması", usage: 9, total: 65, mean: 7.2 },
];

const PIE_COLORS = ["#667eea", "#f093fb", "#4facfe", "#43e97b"];

// ==================== COMPONENT ====================
export default function StatisticsPage() {
  const [isMounted, setIsMounted] = useState(false);

  // Recharts requires a mounted check for hydration safety in modern Next.js
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const handleDownload = () => {
    alert("Karne başarıyla bilgisayarınıza indiriliyor!");
  };

  return (
    <div className={styles.container}>
      
      {/* Header */}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>
          <BarChart2 size={32} color="#0066cc" />
          Performans İstatistikleri
        </h1>
        <button className={styles.btnDownload} onClick={handleDownload}>
          <Download size={20} />
          <span>Karneyi İndir</span>
        </button>
      </div>

      {/* Overview Metrics Grid */}
      <div className={styles.metricsGrid}>
        <div className={`${styles.metricCard} ${styles.bgBluePurple}`}>
          <p className={styles.metricValue}>{mockStats.totalScore}</p>
          <p className={styles.metricLabel}>Toplam Puan</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgPinkRed}`}>
          <p className={styles.metricValue}>{mockStats.totalActions}</p>
          <p className={styles.metricLabel}>Toplam Eylem</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgCyanBlue}`}>
          <p className={styles.metricValue}>{mockStats.averageScore.toFixed(1)}</p>
          <p className={styles.metricLabel}>Ortalama Puan/Eylem</p>
        </div>
        <div className={`${styles.metricCard} ${styles.bgGreenTeal}`}>
          <p className={styles.metricValue}>{mockStats.completedCases}</p>
          <p className={styles.metricLabel}>Tamamlanan Vaka</p>
        </div>
      </div>

      {/* Weakness Detection Alert */}
      <div className={styles.recommendationBox}>
        <Lightbulb size={28} className={styles.recommendationIcon} />
        <div className={styles.recommendationContent}>
          <h3>Gelişim Önerileri</h3>
          <p>{mockRecommendation}</p>
        </div>
      </div>

      {/* Charts Section */}
      {isMounted && (
        <>
          <div className={styles.chartsGrid2}>
            {/* Trend Chart */}
            <div className={styles.chartCard}>
              <h3><TrendingUp size={22} color="#667eea" /> Puan Trendi</h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={mockTrendData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="actionIndex" stroke="#a0aec0" />
                    <YAxis stroke="#a0aec0" />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                    <Line type="monotone" dataKey="cumulative" name="Kümülatif Puan" stroke="#667eea" strokeWidth={4} activeDot={{ r: 8 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Pie Chart */}
            <div className={styles.chartCard}>
              <h3><PieChart size={22} color="#f093fb" /> Vaka Dağılımı</h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={mockPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={80}
                      outerRadius={110}
                      paddingAngle={5}
                      dataKey="value"
                      label={({name, percent}: {name?: string, percent?: number}) => `${name || ''} ${((percent || 0) * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {mockPieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip cursor={{ fill: 'rgba(0,0,0,0.02)' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Histogram Replacement */}
          <div className={styles.chartsGrid1}>
            <div className={styles.chartCard}>
              <h3><Target size={22} color="#4facfe" /> Puan Dağılımı</h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={mockHistogramData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                    <XAxis dataKey="scoreRange" stroke="#a0aec0" />
                    <YAxis stroke="#a0aec0" />
                    <Tooltip cursor={{ fill: 'rgba(0,0,0,0.02)' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
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
              {mockActionHistory.map((item) => (
                <tr key={item.id}>
                  <td>{item.date}</td>
                  <td><strong>{item.case}</strong></td>
                  <td>{item.action}</td>
                  <td>{item.score}</td>
                  <td>
                    <span className={`${styles.tag} ${
                      item.outcome === "Başarılı" ? styles.tagSuccess : 
                      item.outcome === "Kısmi" ? styles.tagWarning : styles.tagInfo
                    }`}>
                      {item.outcome}
                    </span>
                  </td>
                </tr>
              ))}
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
              {mockActionStats.map((stat, idx) => (
                <tr key={idx}>
                  <td><strong>{stat.type}</strong></td>
                  <td>{stat.usage}</td>
                  <td>{stat.total}</td>
                  <td>
                    <span style={{ 
                      color: stat.mean >= 9 ? '#276749' : stat.mean >= 7 ? '#c05621' : '#e53e3e',
                      fontWeight: 700
                    }}>
                      {stat.mean.toFixed(1)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>

    </div>
  );
}
