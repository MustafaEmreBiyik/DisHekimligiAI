"use client";

import React from "react";
import {
  User,
  GraduationCap,
  BarChart3,
  ClipboardList,
  Settings,
  Bell,
  Palette,
  History,
  AlertTriangle,
  Lock,
  ShieldAlert,
  Save,
  Edit3,
  RefreshCcw,
  Trash2,
} from "lucide-react";
import styles from "./Profile.module.css";

export default function ProfilePage() {
  // Mock Data (equivalent to Streamlit fallback data)
  const student = {
    name: "Kullanıcı",
    role: "Öğrenci",
    id: "N/A",
    email: "kullanici@example.com",
    stats: {
      totalSessions: 12,
      completedCases: 8,
      totalActions: 45,
      averageScore: 82.5,
    },
    recentActivity: [
      {
        text: '"Oral Liken Planus" vakası tamamlandı',
        time: "10 Aralık 2025, 14:23",
      },
      {
        text: '"Kronik Periodontitis" vakasına başlandı',
        time: "10 Aralık 2025, 13:45",
      },
      { text: "Profil bilgileri güncellendi", time: "9 Aralık 2025, 16:10" },
      {
        text: '"Primer Herpes" vakası tamamlandı',
        time: "9 Aralık 2025, 11:30",
      },
      { text: "Sistem giriş yapıldı", time: "8 Aralık 2025, 15:20" },
    ],
  };

  const handleFeatureAlert = () => {
    alert("Bu özellik yakında aktif olacak!");
  };

  return (
    <div className={styles.container}>
      {/* Profile Header */}
      <div className={styles.profileHeader}>
        <div className={styles.avatarContainer}>
          <User size={48} color="white" strokeWidth={1.5} />
        </div>
        <h1 className={styles.studentName}>{student.name}</h1>
        <div className={styles.studentRole}>
          <GraduationCap size={18} />
          <span>{student.role}</span>
        </div>
      </div>

      {/* Statistics Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <BarChart3 size={28} color="#0066cc" />
          <h2 className={styles.sectionTitle}>Performans İstatistikleri</h2>
        </div>

        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>
              {student.stats.totalSessions}
            </div>
            <div className={styles.statLabel}>Toplam Oturum</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>
              {student.stats.completedCases}
            </div>
            <div className={styles.statLabel}>Tamamlanan Vaka</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{student.stats.totalActions}</div>
            <div className={styles.statLabel}>Toplam Eylem</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{student.stats.averageScore}</div>
            <div className={styles.statLabel}>Ortalama Puan</div>
          </div>
        </div>
      </section>

      <div className={styles.divider} />

      {/* Account Info Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <ClipboardList size={28} color="#0066cc" />
          <h2 className={styles.sectionTitle}>Hesap Bilgileri</h2>
        </div>

        <div className={styles.grid2}>
          {/* Personal Info */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <User size={20} />
              <h3 className={styles.cardTitle}>Kişisel Bilgiler</h3>
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Ad Soyad</label>
              <input
                type="text"
                className={styles.input}
                value={student.name}
                disabled
              />
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Öğrenci Numarası</label>
              <input
                type="text"
                className={styles.input}
                value={student.id}
                disabled
              />
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>E-posta</label>
              <input
                type="email"
                className={styles.input}
                value={student.email}
                disabled
              />
            </div>

            <button className={styles.btnPrimary} onClick={handleFeatureAlert}>
              <Edit3 size={18} />
              Bilgilerimi Güncelle
            </button>
          </div>

          {/* Security */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <Lock size={20} />
              <h3 className={styles.cardTitle}>Güvenlik</h3>
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Mevcut Şifre</label>
              <input
                type="password"
                className={styles.input}
                placeholder="••••••••"
                disabled
              />
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Yeni Şifre</label>
              <input
                type="password"
                className={styles.input}
                placeholder="••••••••"
                disabled
              />
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Yeni Şifre (Tekrar)</label>
              <input
                type="password"
                className={styles.input}
                placeholder="••••••••"
                disabled
              />
            </div>

            <button
              className={styles.btnSecondary}
              onClick={handleFeatureAlert}
              style={{ marginTop: "auto" }}
            >
              <Lock size={18} />
              Şifremi Değiştir
            </button>
          </div>
        </div>
      </section>

      <div className={styles.divider} />

      {/* Settings Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <Settings size={28} color="#0066cc" />
          <h2 className={styles.sectionTitle}>Ayarlar</h2>
        </div>

        <div className={styles.grid2}>
          {/* Notifications */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <Bell size={20} />
              <h3 className={styles.cardTitle}>Bildirim Tercihleri</h3>
            </div>

            <div className={styles.checkboxGroup}>
              <input
                type="checkbox"
                className={styles.checkbox}
                checked
                disabled
              />
              <span className={styles.checkboxLabel}>E-posta bildirimleri</span>
            </div>
            <div className={styles.checkboxGroup}>
              <input
                type="checkbox"
                className={styles.checkbox}
                checked
                disabled
              />
              <span className={styles.checkboxLabel}>
                Haftalık ilerleme raporu
              </span>
            </div>
            <div className={styles.checkboxGroup}>
              <input type="checkbox" className={styles.checkbox} disabled />
              <span className={styles.checkboxLabel}>
                Yeni vaka bildirimleri
              </span>
            </div>

            <button className={styles.btnPrimary} onClick={handleFeatureAlert}>
              <Save size={18} />
              Bildirimleri Kaydet
            </button>
          </div>

          {/* Appearance Settings */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <Palette size={20} />
              <h3 className={styles.cardTitle}>Görünüm Ayarları</h3>
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Tema</label>
              <select className={styles.select} disabled>
                <option>Sistem</option>
                <option>Açık</option>
                <option>Koyu</option>
              </select>
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Dil</label>
              <select className={styles.select} disabled>
                <option>Türkçe</option>
                <option>English</option>
              </select>
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Font Boyutu</label>
              <input
                type="range"
                className={styles.input}
                min="12"
                max="20"
                value="14"
                disabled
                style={{ padding: 0 }}
              />
            </div>

            <button className={styles.btnPrimary} onClick={handleFeatureAlert}>
              <Save size={18} />
              Ayarları Kaydet
            </button>
          </div>
        </div>
      </section>

      <div className={styles.divider} />

      {/* Recent Activity */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <History size={28} color="#0066cc" />
          <h2 className={styles.sectionTitle}>Son Aktiviteler</h2>
        </div>

        <div className={`${styles.card} ${styles.activityCard}`}>
          <div className={styles.activityList}>
            {student.recentActivity.map((activity, index) => (
              <div key={index} className={styles.activityItem}>
                <div className={styles.activityDot}></div>
                <div className={styles.activityContent}>
                  <div className={styles.activityText}>{activity.text}</div>
                  <div className={styles.activityTime}>{activity.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className={styles.divider} />

      {/* Danger Zone */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <AlertTriangle size={28} color="#e53e3e" />
          <h2 className={styles.sectionTitle} style={{ color: "#e53e3e" }}>
            Tehlikeli Bölge
          </h2>
        </div>

        <div className={`${styles.card} ${styles.dangerCard}`}>
          <div className={styles.cardHeader} style={{ color: "#c53030" }}>
            <ShieldAlert size={20} />
            <h3 className={styles.cardTitle}>Hesap Yönetimi</h3>
          </div>

          <div className={styles.dangerWarning}>
            <AlertTriangle size={18} />
            <span>Dikkat: Bu işlemler geri alınamaz!</span>
          </div>

          <div
            className={styles.grid2}
            style={{ gap: "1rem", marginTop: "1rem" }}
          >
            <button className={styles.btnDanger} onClick={handleFeatureAlert}>
              <RefreshCcw size={18} />
              Tüm İlerlememi Sıfırla
            </button>
            <button
              className={styles.btnDangerSolid}
              onClick={handleFeatureAlert}
            >
              <Trash2 size={18} />
              Hesabımı Sil
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <p>
          📧 Destek:{" "}
          <a href="mailto:betul.danismaz@istun.edu.tr">
            betul.danismaz@istun.edu.tr
          </a>{" "}
          | 🔐 Gizlilik Politikası | 📜 Kullanım Koşulları
        </p>
        <p>
          <small>Son güncelleme: Aralık 2025</small>
        </p>
      </footer>
    </div>
  );
}
