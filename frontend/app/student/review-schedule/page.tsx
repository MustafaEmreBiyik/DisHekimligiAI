"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  reviewScheduleAPI,
  ReviewScheduleItem,
  SubmitReviewResult,
} from "@/lib/api";
import {
  Brain,
  CheckCircle2,
  Clock,
  ArrowRight,
  Trophy,
  RotateCcw,
} from "lucide-react";

const RATINGS = [
  { value: 0, label: "Hiç hatırlamadım", color: "#c53030", bg: "#fff5f5", border: "#fc8181" },
  { value: 1, label: "Yanlış cevap",      color: "#c05621", bg: "#fffaf0", border: "#f6ad55" },
  { value: 2, label: "Zor hatırladım",    color: "#b7791f", bg: "#fffff0", border: "#f6e05e" },
  { value: 3, label: "Güçlükle doğru",    color: "#2b6cb0", bg: "#ebf8ff", border: "#90cdf4" },
  { value: 4, label: "Tereddütle doğru",  color: "#276749", bg: "#f0fff4", border: "#9ae6b4" },
  { value: 5, label: "Mükemmel",          color: "#22543d", bg: "#f0fff4", border: "#38a169" },
];

export default function ReviewSchedulePage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [items, setItems] = useState<ReviewScheduleItem[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [doneCount, setDoneCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<SubmitReviewResult | null>(null);
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!user) return;
    reviewScheduleAPI
      .getDueItems()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [user]);

  const currentItem: ReviewScheduleItem | undefined = items[currentIdx];
  const totalItems = items.length;
  const progressPct = totalItems > 0 ? (doneCount / totalItems) * 100 : 0;
  const isComplete = doneCount > 0 && doneCount === totalItems;

  const handleRate = async (rating: number) => {
    if (!currentItem || submitting) return;
    setSubmitting(true);
    try {
      const result = await reviewScheduleAPI.submitResult(currentItem.id, rating);
      setLastResult(result);
    } catch {
      setLastResult(null);
    } finally {
      setSubmitting(false);
      setDoneCount((p) => p + 1);
      setShowResult(true);
    }
  };

  const handleNext = () => {
    setShowResult(false);
    setLastResult(null);
    setCurrentIdx((p) => p + 1);
  };

  if (authLoading || loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
        <div style={{ width: 36, height: 36, border: "4px solid #e2e8f0", borderTopColor: "#805ad5", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      </div>
    );
  }

  if (isComplete) {
    return (
      <div style={{ maxWidth: 520, margin: "5rem auto", padding: "0 1.5rem", textAlign: "center" }}>
        <Trophy size={60} color="#d69e2e" style={{ marginBottom: "1rem" }} />
        <h2 style={{ fontSize: "1.6rem", fontWeight: 700, color: "#1a202c", margin: "0 0 0.5rem" }}>
          Harika iş!
        </h2>
        <p style={{ color: "#718096", marginBottom: "2rem", lineHeight: 1.6 }}>
          Bugünkü <strong>{totalItems}</strong> tekrar kartını tamamladın.
          <br />SM-2 algoritması bir sonraki tekrar tarihini hesapladı.
        </p>
        <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
          <button
            onClick={() => { setItems([]); setCurrentIdx(0); setDoneCount(0); setLoading(true); reviewScheduleAPI.getDueItems().then(setItems).catch(() => setItems([])).finally(() => setLoading(false)); }}
            style={{ background: "#fff", color: "#805ad5", border: "1.5px solid #805ad5", borderRadius: "8px", padding: "10px 20px", fontSize: "0.95rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
            <RotateCcw size={16} /> Yenile
          </button>
          <button
            onClick={() => router.push("/quiz")}
            style={{ background: "#805ad5", color: "#fff", border: "none", borderRadius: "8px", padding: "10px 20px", fontSize: "0.95rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
            Quiz'e Git <ArrowRight size={16} />
          </button>
        </div>
      </div>
    );
  }

  if (totalItems === 0) {
    return (
      <div style={{ maxWidth: 520, margin: "5rem auto", padding: "0 1.5rem", textAlign: "center" }}>
        <CheckCircle2 size={60} color="#38a169" style={{ marginBottom: "1rem" }} />
        <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#1a202c", margin: "0 0 0.5rem" }}>
          Bugün tekrar kartı yok
        </h2>
        <p style={{ color: "#718096", marginBottom: "2rem", lineHeight: 1.6 }}>
          Yanlış cevapladığın sorular otomatik olarak buraya eklenir ve SM-2 algoritması uygun zamanda tekrar sunar.
        </p>
        <button
          onClick={() => router.push("/quiz")}
          style={{ background: "#3182ce", color: "#fff", border: "none", borderRadius: "8px", padding: "10px 20px", fontSize: "0.95rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "6px" }}
        >
          Quiz Çöz <ArrowRight size={16} />
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "1.25rem" }}>
        <Brain size={28} color="#805ad5" />
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: "1.35rem", fontWeight: 700, color: "#1a202c", margin: 0 }}>
            Tekrar Programı
          </h1>
          <p style={{ fontSize: "0.8rem", color: "#718096", margin: 0 }}>
            SM-2 aralıklı tekrar algoritması
          </p>
        </div>
        <span style={{ fontSize: "0.9rem", color: "#4a5568", display: "flex", alignItems: "center", gap: "5px" }}>
          <Clock size={15} />
          {doneCount}/{totalItems}
        </span>
      </div>

      {/* Progress bar */}
      <div style={{ background: "#e2e8f0", borderRadius: "999px", height: "7px", marginBottom: "2rem", overflow: "hidden" }}>
        <div
          style={{
            background: "linear-gradient(90deg, #805ad5, #b794f4)",
            borderRadius: "999px",
            height: "100%",
            width: `${progressPct}%`,
            transition: "width 0.4s ease",
          }}
        />
      </div>

      {/* Question card */}
      {!showResult ? (
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "2rem", boxShadow: "0 2px 12px rgba(0,0,0,0.06)", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "1rem" }}>
            <span style={{ background: "#e9d8fd", color: "#6b46c1", fontSize: "0.75rem", fontWeight: 600, borderRadius: "999px", padding: "3px 10px" }}>
              {currentItem.topic_id}
            </span>
            <span style={{ fontSize: "0.75rem", color: "#a0aec0" }}>
              {currentIdx + 1} / {totalItems}
            </span>
          </div>

          <p style={{ fontSize: "1.05rem", color: "#1a202c", lineHeight: 1.75, margin: "0 0 1.25rem" }}>
            {currentItem.question_text}
          </p>

          <div style={{ display: "flex", gap: "16px", fontSize: "0.78rem", color: "#a0aec0", borderTop: "1px solid #f7fafc", paddingTop: "0.75rem" }}>
            <span>{currentItem.repetitions}. tekrar</span>
            <span>Mevcut aralık: {currentItem.interval_days} gün</span>
            {currentItem.last_reviewed_at && (
              <span>Son: {new Date(currentItem.last_reviewed_at).toLocaleDateString("tr-TR")}</span>
            )}
          </div>
        </div>
      ) : (
        /* Result card */
        <div style={{ background: "#f0fff4", border: "1px solid #9ae6b4", borderRadius: "12px", padding: "2rem", marginBottom: "1.5rem", textAlign: "center" }}>
          <CheckCircle2 size={40} color="#38a169" style={{ marginBottom: "0.75rem" }} />
          {lastResult ? (
            <>
              <p style={{ fontWeight: 600, color: "#276749", fontSize: "1rem", margin: "0 0 0.3rem" }}>
                Kaydedildi!
              </p>
              <p style={{ color: "#4a5568", fontSize: "0.9rem", margin: 0 }}>
                Sonraki tekrar:{" "}
                <strong>{new Date(lastResult.next_due_date).toLocaleDateString("tr-TR")}</strong>{" "}
                <span style={{ color: "#718096" }}>({lastResult.next_interval_days} gün sonra)</span>
              </p>
            </>
          ) : (
            <p style={{ color: "#4a5568", fontSize: "0.9rem", margin: 0 }}>Cevap kaydedildi.</p>
          )}
        </div>
      )}

      {/* Rating buttons / Next button */}
      {!showResult ? (
        <div>
          <p style={{ fontSize: "0.83rem", color: "#718096", textAlign: "center", marginBottom: "0.75rem" }}>
            Bu soruyu ne kadar iyi hatırladın?
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px" }}>
            {RATINGS.map((r) => (
              <button
                key={r.value}
                onClick={() => handleRate(r.value)}
                disabled={submitting}
                style={{
                  background: r.bg,
                  border: `1.5px solid ${r.border}`,
                  borderRadius: "8px",
                  color: r.color,
                  cursor: submitting ? "not-allowed" : "pointer",
                  opacity: submitting ? 0.55 : 1,
                  padding: "10px 6px",
                  fontSize: "0.76rem",
                  fontWeight: 600,
                  textAlign: "center",
                  lineHeight: 1.3,
                  transition: "opacity 0.15s",
                }}
              >
                <span style={{ fontSize: "1.1rem", display: "block", marginBottom: "3px" }}>{r.value}</span>
                {r.label}
              </button>
            ))}
          </div>
          <p style={{ fontSize: "0.74rem", color: "#cbd5e0", textAlign: "center", marginTop: "0.6rem" }}>
            0–2: yanlış &nbsp;|&nbsp; 3–5: doğru &nbsp;|&nbsp; ≥3 tekrar ilerler
          </p>
        </div>
      ) : (
        <div style={{ textAlign: "center" }}>
          <button
            onClick={handleNext}
            style={{
              background: currentIdx < totalItems - 1 ? "#805ad5" : "#38a169",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              padding: "12px 32px",
              fontSize: "1rem",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {currentIdx < totalItems - 1 ? (
              <><ArrowRight size={18} /> Sonraki Kart</>
            ) : (
              <><Trophy size={18} /> Tamamla</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
