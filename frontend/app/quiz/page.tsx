"use client";

import { useState, useMemo, useEffect } from "react";
import {
  FileQuestion,
  CheckCircle2,
  XOctagon,
  Info,
  RotateCcw,
  Search,
} from "lucide-react";
import styles from "./Quiz.module.css";
import { quizAPI, QuizQuestion, QuizQuestionResult, QuizSubmitResponse, explanationAPI, AnswerExplanationResponse } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";

export default function QuizPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // S8B safety constraint: assessment mode defaults to safe (reserved for future feature flag).
  // const isAssessmentMode = true;
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [topics, setTopics] = useState<string[]>(["Tümü"]);
  const [selectedTopic, setSelectedTopic] = useState<string>("Tümü");
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(true);
  // Populated after server-side grading
  const [gradeResults, setGradeResults] = useState<Record<string, QuizQuestionResult>>({});
  const [serverScore, setServerScore] = useState<QuizSubmitResponse | null>(null);
  // S10-B: "Why this score?" explanation panel state
  const [openExplanation, setOpenExplanation] = useState<string | null>(null);
  const [explanationData, setExplanationData] = useState<Record<string, AnswerExplanationResponse>>({});
  const [loadingExplanation, setLoadingExplanation] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      loadQuestions();
    }
  }, [user]);

  const loadQuestions = async () => {
    setIsLoadingQuestions(true);
    try {
      const [questionsData, topicsData] = await Promise.all([
        quizAPI.getQuestions(),
        quizAPI.getTopics().catch(() => null),
      ]);
      setQuestions(questionsData);
      if (topicsData && Array.isArray(topicsData)) {
        setTopics(topicsData);
      } else {
        const uniqueTopics = Array.from(new Set(questionsData.map((q: QuizQuestion) => q.topic))) as string[];
        setTopics(["Tümü", ...uniqueTopics]);
      }
    } catch (err) {
      console.error("Failed to load questions:", err);
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  const filteredQuestions = useMemo(() => {
    if (selectedTopic === "Tümü") return questions;
    return questions.filter((q) => q.topic === selectedTopic);
  }, [selectedTopic, questions]);

  const handleSelectOption = (questionId: string, option: string) => {
    if (isSubmitted) return;
    setUserAnswers((prev) => ({ ...prev, [questionId]: option }));
  };

  const allAnswered =
    filteredQuestions.length > 0 &&
    filteredQuestions.every((q) => userAnswers[q.id]?.trim());

  const handleReset = () => {
    setUserAnswers({});
    setIsSubmitted(false);
    setGradeResults({});
    setServerScore(null);
    setOpenExplanation(null);
    setExplanationData({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleToggleExplanation = async (questionId: string, answerId?: number | null) => {
    if (openExplanation === questionId) {
      setOpenExplanation(null);
      return;
    }
    setOpenExplanation(questionId);
    if (!answerId || explanationData[questionId] || !serverScore) return;
    setLoadingExplanation(questionId);
    try {
      const data = await explanationAPI.getAnswerExplanation(serverScore.attempt_id, answerId);
      setExplanationData((prev) => ({ ...prev, [questionId]: data }));
    } catch {
      // silent — explanation is non-critical
    } finally {
      setLoadingExplanation(null);
    }
  };

  useEffect(() => {
    handleReset();
  }, [selectedTopic]);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const response: QuizSubmitResponse = await quizAPI.submitAnswers(userAnswers);
      const resultsMap: Record<string, QuizQuestionResult> = {};
      response.results.forEach((r) => { resultsMap[r.id] = r; });
      setGradeResults(resultsMap);
      setServerScore(response);
      setIsSubmitted(true);
    } catch (err) {
      console.error("Failed to submit quiz:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const correctCount = serverScore?.score ?? 0;
  const totalCount = serverScore?.total ?? filteredQuestions.length;
  const scorePercentage = serverScore?.percentage ?? 0;

  let feedbackLabel = "";
  let feedbackIcon = "📚";
  let progressColor = "#e53e3e";

  const isPending = serverScore?.overall_status === "PENDING";

  if (isPending) {
    feedbackLabel = "Değerlendirme Bekleniyor";
    feedbackIcon = "⏳";
    progressColor = "#ecc94b";
  } else if (scorePercentage >= 80) {
    feedbackLabel = "Mükemmel!";
    feedbackIcon = "🏆";
    progressColor = "#38a169";
  } else if (scorePercentage >= 60) {
    feedbackLabel = "İyi!";
    feedbackIcon = "👍";
    progressColor = "#3182ce";
  } else if (isSubmitted) {
    feedbackLabel = "Daha fazla çalışma gerekli";
    progressColor = "#e53e3e";
  }

  if (authLoading) return null;

  return (
    <div className={styles.container}>
      {/* HEADER */}
      <div className={styles.header}>
        <h1 className={styles.title}>
          <FileQuestion size={36} color="#0066cc" />
          Diş Hekimliği Klinik Bilgi Testi
        </h1>
        <p className={styles.subtitle}>
          Teorik bilginizi ölçün ve güçlü/zayıf alanlarınızı keşfedin
        </p>
      </div>

      {/* TOPIC SELECTOR */}
      <div className={styles.topicSelector}>
        {topics.map((topic) => (
          <button
            key={topic}
            className={styles.topicBtn}
            data-active={selectedTopic === topic}
            onClick={() => setSelectedTopic(topic)}
            disabled={isSubmitted}
            style={isSubmitted ? { opacity: 0.6, cursor: "not-allowed" } : {}}
          >
            {topic}
          </button>
        ))}
      </div>

      {isLoadingQuestions ? (
        <div style={{ textAlign: "center", padding: "3rem", color: "#718096" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              border: "4px solid #e2e8f0",
              borderTopColor: "#3182ce",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
              margin: "0 auto 1rem",
            }}
          />
          <p>Sorular yükleniyor...</p>
        </div>
      ) : filteredQuestions.length === 0 ? (
        <div style={{ textAlign: "center", padding: "3rem", color: "#718096" }}>
          <Search
            size={48}
            style={{ opacity: 0.2, marginBottom: "1rem", display: "inline-block" }}
          />
          <h3>Bu konu için henüz soru eklenmedi.</h3>
        </div>
      ) : (
        <>
          {/* QUESTIONS LIST */}
          <div className={styles.questionsList}>
            {filteredQuestions.map((q, idx) => {
              const selectedAnswer = userAnswers[q.id];
              const result = gradeResults[q.id];

              return (
                <div key={q.id} className={styles.questionCard}>
                  <div className={styles.questionNum}>Soru {idx + 1}</div>
                  <div className={styles.questionText}>{q.question}</div>

                  {q.question_type === "OPEN_ENDED" ? (
                    <div className={styles.optionsList}>
                      <textarea
                        placeholder="Yanıtınızı buraya yazınız..."
                        value={selectedAnswer || ""}
                        onChange={(e) => handleSelectOption(q.id, e.target.value)}
                        disabled={isSubmitted}
                        rows={4}
                        style={{ width: "100%", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}
                      />
                    </div>
                  ) : (
                    <div className={styles.optionsList}>
                      {q.options.map((option) => {
                        const isSelected = selectedAnswer === option;

                        let isCorrectOption = false;
                        let isWrongOption = false;

                        if (isSubmitted && result) {
                          isCorrectOption = option === result.selected_option && result.is_correct === true;
                          isWrongOption = option === result.selected_option && result.is_correct === false;
                        }

                        return (
                          <div
                            key={option}
                            className={`${styles.option} ${isSubmitted ? styles.optionDisabled : ""}`}
                            data-selected={isSelected && !isSubmitted}
                            data-correct={isCorrectOption}
                            data-wrong={isWrongOption}
                            onClick={() => handleSelectOption(q.id, option)}
                          >
                            <div className={styles.optionRadio}>
                              {isCorrectOption ? (
                                <CheckCircle2 size={16} />
                              ) : isWrongOption ? (
                                <XOctagon size={16} />
                              ) : null}
                            </div>
                            <span>{option}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* FEEDBACK — only after server grading */}
                  {isSubmitted && result && (
                    <div className={styles.explanation}>
                      <Info size={24} style={{ flexShrink: 0, marginTop: "2px" }} />
                      <div>
                        {result.grading_status === 'PENDING' ? (
                          <>
                            <strong>Durum:</strong>
                            <p style={{ margin: "0.25rem 0 0 0" }}>Açık uçlu sorunuz eğitmen değerlendirmesi için sıraya alındı.</p>
                          </>
                        ) : result.grading_status === 'PUBLISHED' && q.question_type === 'OPEN_ENDED' ? (
                          <>
                            <strong>Eğitmen Geri Bildirimi (Puan: {result.instructor_score}):</strong>
                            <p style={{ margin: "0.25rem 0 0 0" }}>{result.instructor_feedback || "Geri bildirim girilmemiş."}</p>
                          </>
                        ) : (
                          <>
                            <strong>Geri Bildirim:</strong>
                            <p style={{ margin: "0.25rem 0 0 0" }}>{result.feedback}</p>
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  {/* S10-B: "Why this score?" expandable panel */}
                  {isSubmitted && result && result.answer_id && (
                    <div style={{ marginTop: "0.75rem" }}>
                      <button
                        onClick={() => handleToggleExplanation(q.id, result.answer_id)}
                        style={{
                          background: "none",
                          border: "1px solid #3182ce",
                          borderRadius: "6px",
                          color: "#3182ce",
                          cursor: "pointer",
                          fontSize: "0.82rem",
                          padding: "4px 10px",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        <Info size={14} />
                        {openExplanation === q.id ? "Kapat" : "Neden bu puan?"}
                      </button>

                      {openExplanation === q.id && (
                        <div
                          style={{
                            marginTop: "0.5rem",
                            padding: "12px",
                            background: "#ebf8ff",
                            borderRadius: "8px",
                            borderLeft: "3px solid #3182ce",
                            fontSize: "0.88rem",
                            lineHeight: "1.6",
                          }}
                        >
                          {loadingExplanation === q.id ? (
                            <p style={{ color: "#718096" }}>Yükleniyor...</p>
                          ) : explanationData[q.id] ? (
                            <>
                              {explanationData[q.id].ai_score_rationale && (
                                <div style={{ marginBottom: "0.5rem" }}>
                                  <strong>AI Değerlendirmesi:</strong>
                                  <p style={{ margin: "0.25rem 0 0" }}>{explanationData[q.id].ai_score_rationale}</p>
                                </div>
                              )}
                              {explanationData[q.id].rubric_guide && (
                                <div style={{ marginBottom: "0.5rem" }}>
                                  <strong>Değerlendirme Kriteri:</strong>
                                  <p style={{ margin: "0.25rem 0 0", whiteSpace: "pre-wrap" }}>{explanationData[q.id].rubric_guide}</p>
                                </div>
                              )}
                              {explanationData[q.id].rubric_version_snapshot && (
                                <p style={{ margin: "0.25rem 0 0", color: "#718096", fontSize: "0.78rem" }}>
                                  Rubrik v{explanationData[q.id].rubric_version_snapshot!.version}
                                </p>
                              )}
                              {!explanationData[q.id].ai_score_rationale && !explanationData[q.id].rubric_guide && (
                                <p style={{ color: "#718096" }}>Bu soru için henüz açıklama mevcut değil.</p>
                              )}
                            </>
                          ) : (
                            <p style={{ color: "#718096" }}>Açıklama yüklenemedi.</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* ACTION BUTTON */}
          {!isSubmitted && (
            <div className={styles.actionContainer}>
              <button
                className={styles.btnPrimary}
                onClick={handleSubmit}
                disabled={!allAnswered || isSubmitting}
              >
                <CheckCircle2 size={20} />
                {isSubmitting ? "Kontrol ediliyor..." : "Cevapları Kontrol Et"}
              </button>
            </div>
          )}

          {/* RESULTS DASHBOARD */}
          {isSubmitted && (
            <div className={styles.resultsBoard}>
              <div className={styles.resultsIcon}>{feedbackIcon}</div>
              <h2 className={styles.resultsTitle}>{feedbackLabel}</h2>
              <p className={styles.resultsDesc}>
                {isPending 
                  ? "Testi tamamladınız. Açık uçlu sorularınızın değerlendirilmesi bittikten sonra toplam puanınız hesaplanacaktır." 
                  : `Testi tamamladınız. Toplam ${totalCount} üzerinden performansınız aşağıda gösterilmektedir.`}
              </p>

              {!isPending && (
                <>
                  <div className={styles.progressBarBg}>
                    <div
                      className={styles.progressBarFill}
                      style={{
                        width: `${scorePercentage}%`,
                        backgroundColor: progressColor,
                      }}
                    />
                  </div>

                  <div className={styles.statsGrid}>
                    <div className={styles.statItem}>
                      <div className={styles.statValue} data-color="blue">
                        {scorePercentage}%
                      </div>
                      <div className={styles.statLabel}>Başarı Oranı</div>
                    </div>
                    <div className={styles.statItem}>
                      <div className={styles.statValue} data-color="green">
                        {correctCount}
                      </div>
                      <div className={styles.statLabel}>Kazanılan Puan</div>
                    </div>
                    <div className={styles.statItem}>
                      <div className={styles.statValue} data-color="red">
                        {totalCount - correctCount}
                      </div>
                      <div className={styles.statLabel}>Kayıp Puan</div>
                    </div>
                  </div>
                </>
              )}

              <button className={styles.btnReset} onClick={handleReset}>
                <RotateCcw size={18} />
                Testi Sıfırla
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
