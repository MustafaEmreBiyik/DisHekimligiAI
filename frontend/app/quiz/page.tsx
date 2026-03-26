"use client";

import React, { useState, useMemo, useEffect } from "react";
import {
  FileQuestion,
  CheckCircle2,
  XOctagon,
  Info,
  RotateCcw,
  Search,
} from "lucide-react";
import styles from "./Quiz.module.css";
import { quizAPI } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";

interface Question {
  id: string;
  topic: string;
  question: string;
  options: string[];
  correct_option: string;
  explanation: string;
}

export default function QuizPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [questions, setQuestions] = useState<Question[]>([]);
  const [topics, setTopics] = useState<string[]>(["Tümü"]);
  const [selectedTopic, setSelectedTopic] = useState<string>("Tümü");
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(true);

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
        // Derive topics from questions
        const uniqueTopics = Array.from(new Set(questionsData.map((q: Question) => q.topic))) as string[];
        setTopics(["Tümü", ...uniqueTopics]);
      }
    } catch (err) {
      console.error("Failed to load questions:", err);
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  // Filter questions by selected topic
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
    filteredQuestions.every((q) => userAnswers[q.id]);

  const handleReset = () => {
    setUserAnswers({});
    setIsSubmitted(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    handleReset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTopic]);

  let correctCount = 0;
  if (isSubmitted) {
    filteredQuestions.forEach((q) => {
      if (userAnswers[q.id] === q.correct_option) {
        correctCount++;
      }
    });
  }
  const totalCount = filteredQuestions.length;
  const scorePercentage =
    totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0;

  let feedbackLabel = "";
  let feedbackIcon = "📚";
  let progressColor = "#e53e3e";

  if (scorePercentage >= 80) {
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
              const isCorrectAnswer = selectedAnswer === q.correct_option;

              return (
                <div key={q.id} className={styles.questionCard}>
                  <div className={styles.questionNum}>Soru {idx + 1}</div>
                  <div className={styles.questionText}>{q.question}</div>

                  <div className={styles.optionsList}>
                    {q.options.map((option) => {
                      const isSelected = selectedAnswer === option;

                      let isCorrectOption = false;
                      let isWrongOption = false;

                      if (isSubmitted) {
                        isCorrectOption = option === q.correct_option;
                        isWrongOption = isSelected && !isCorrectAnswer;
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

                  {/* EXPLANATION */}
                  {isSubmitted && (
                    <div className={styles.explanation}>
                      <Info size={24} style={{ flexShrink: 0, marginTop: "2px" }} />
                      <div>
                        <strong>Açıklama:</strong>
                        <p style={{ margin: "0.25rem 0 0 0" }}>{q.explanation}</p>
                      </div>
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
                onClick={() => setIsSubmitted(true)}
                disabled={!allAnswered}
              >
                <CheckCircle2 size={20} />
                Cevapları Kontrol Et
              </button>
            </div>
          )}

          {/* RESULTS DASHBOARD */}
          {isSubmitted && (
            <div className={styles.resultsBoard}>
              <div className={styles.resultsIcon}>{feedbackIcon}</div>
              <h2 className={styles.resultsTitle}>{feedbackLabel}</h2>
              <p className={styles.resultsDesc}>
                Testi tamamladınız. Toplam {totalCount} soru üzerinden
                performansınız aşağıda gösterilmektedir.
              </p>

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
                  <div className={styles.statLabel}>Doğru</div>
                </div>
                <div className={styles.statItem}>
                  <div className={styles.statValue} data-color="red">
                    {totalCount - correctCount}
                  </div>
                  <div className={styles.statLabel}>Yanlış</div>
                </div>
              </div>

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
