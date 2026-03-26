"use client";

import React, { useEffect, useState } from "react";
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
import { useAuth } from "@/context/AuthContext";
import { authAPI, userAPI } from "@/lib/api";
import { useRouter } from "next/navigation";

interface UserInfo {
  student_id: string;
  name: string;
  email?: string;
}

interface UserStats {
  total_sessions: number;
  completed_cases: number;
  total_actions: number;
  average_score: number;
}

export default function ProfilePage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [stats, setStats] = useState<UserStats>({
    total_sessions: 0,
    completed_cases: 0,
    total_actions: 0,
    average_score: 0,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      loadData();
    }
  }, [user]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Fetch user info and stats in parallel
      const [meData, statsData] = await Promise.all([
        authAPI.getCurrentUser().catch(() => null),
        userAPI.getStats().catch(() => null),
      ]);

      if (meData) {
        setUserInfo(meData);
      } else {
        // Fallback to auth context data
        setUserInfo({ student_id: user!.student_id, name: user!.name });
      }

      if (statsData) {
        setStats({
          total_sessions: statsData.total_sessions ?? 0,
          completed_cases: statsData.completed_cases ?? 0,
          total_actions: statsData.total_actions ?? 0,
          average_score: statsData.average_score ?? 0,
        });
      }
    } catch (err) {
      console.error("Failed to load profile data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeatureAlert = () => {
    alert("Bu özellik yakında aktif olacak!");
  };

  if (authLoading || (!user && !isLoading)) return null;

  const displayName = userInfo?.name ?? user?.name ?? "Kullanıcı";
  const displayId = userInfo?.student_id ?? user?.student_id ?? "N/A";
  const displayEmail = userInfo?.email ?? "";

  return (
    <div className={styles.container}>
      {/* Profile Header */}
      <div className={styles.profileHeader}>
        <div className={styles.avatarContainer}>
          <User size={48} color="white" strokeWidth={1.5} />
        </div>
        <h1 className={styles.studentName}>{displayName}</h1>
        <div className={styles.studentRole}>
          <GraduationCap size={18} />
          <span>Öğrenci</span>
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
              {isLoading ? "—" : stats.total_sessions}
            </div>
            <div className={styles.statLabel}>Toplam Oturum</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>
              {isLoading ? "—" : stats.completed_cases}
            </div>
            <div className={styles.statLabel}>Tamamlanan Vaka</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>
              {isLoading ? "—" : stats.total_actions}
            </div>
            <div className={styles.statLabel}>Toplam Eylem</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>
              {isLoading ? "—" : stats.average_score.toFixed(1)}
            </div>
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
                value={displayName}
                disabled
              />
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>Öğrenci Numarası</label>
              <input
                type="text"
                className={styles.input}
                value={displayId}
                disabled
              />
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>E-posta</label>
              <input
                type="email"
                className={styles.input}
                value={displayEmail}
                placeholder="—"
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
              <input type="checkbox" className={styles.checkbox} checked disabled />
              <span className={styles.checkboxLabel}>E-posta bildirimleri</span>
            </div>
            <div className={styles.checkboxGroup}>
              <input type="checkbox" className={styles.checkbox} checked disabled />
              <span className={styles.checkboxLabel}>Haftalık ilerleme raporu</span>
            </div>
            <div className={styles.checkboxGroup}>
              <input type="checkbox" className={styles.checkbox} disabled />
              <span className={styles.checkboxLabel}>Yeni vaka bildirimleri</span>
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
                defaultValue="14"
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

          <div className={styles.grid2} style={{ gap: "1rem", marginTop: "1rem" }}>
            <button className={styles.btnDanger} onClick={handleFeatureAlert}>
              <RefreshCcw size={18} />
              Tüm İlerlememi Sıfırla
            </button>
            <button className={styles.btnDangerSolid} onClick={handleFeatureAlert}>
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
