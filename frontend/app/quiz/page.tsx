"use client";

import React, { useState, useMemo, useEffect } from "react";
import { 
  FileQuestion, 
  CheckCircle2, 
  XOctagon, 
  Info, 
  RotateCcw, 
  Search
} from "lucide-react";
import styles from "./Quiz.module.css";

// --- TYPES & MOCK DATA ---
interface Question {
  id: string;
  topic: string;
  question: string;
  options: string[];
  correct_option: string;
  explanation: string;
}

const mockQuestions: Question[] = [
  {
    id: "q_oral_pat_1",
    topic: "Oral Patoloji",
    question: "Aşağıdakilerden hangisi oral liken planusun (OLP) klinik varyantlarından biri değildir?",
    options: ["Retiküler", "Eroziv", "Büllöz", "Kavernöz"],
    correct_option: "Kavernöz",
    explanation: "Oral Liken Planusun retiküler, eroziv, atrofik, büllöz, plak benzeri ve papüler olmak üzere 6 klinik tipi vardır. 'Kavernöz' bir hemanjiom alt tipidir, OLP klinik varyantı değildir."
  },
  {
    id: "q_oral_pat_2",
    topic: "Oral Patoloji",
    question: "Tükürük bezi tümörleri arasında en sık görülen iyi huylu tümör hangisidir?",
    options: ["Warthin Tümörü", "Pleomorfik Adenom", "Mukoepidermoid Karsinom", "Basal Hücreli Adenom"],
    correct_option: "Pleomorfik Adenom",
    explanation: "Pleomorfik adenom (benign mikst tümör), hem majör hem de minör tükürük bezlerinde en sık izlenen benign tükürük bezi tümörüdür."
  },
  {
    id: "q_enf_1",
    topic: "Enfeksiyöz Hastalıklar",
    question: "Diş hekimliği kliniklerinde hepatit B (HBV) enfeksiyonu riskinin yüksek olmasının temel nedeni nedir?",
    options: ["Sadece tükürükle bulaşması", "Virüsün kurumuş kanda oda sıcaklığında 7 güne kadar canlı kalabilmesi", "Aerosollerle bulaşma riskinin çok yüksek olması", "Kuluçka süresinin çok kısa olması"],
    correct_option: "Virüsün kurumuş kanda oda sıcaklığında 7 güne kadar canlı kalabilmesi",
    explanation: "HBV oldukça dirençli bir virüstür. Tıbbi araçlar üzerinde veya kurumuş kanda oda sıcaklığında 1 haftaya kadar enfektivitesini koruyabilir. HBsAg+ kan oldukça bulaştırıcıdır."
  },
  {
    id: "q_travma_1",
    topic: "Travmatik Lezyonlar",
    question: "Kalıcı bir dişin total avülsiyonu vakasında, dişin kliniğe ulaştırılması için en ideal transport medyumları hangi seçenekte doğru olarak verilmiştir?",
    options: ["Kuru peçete - Su", "Süt - HBSS (Hank's Balanced Salt Solution) - Tükürük", "Alkol - Serum Fizyolojik", "Sıcak Su - Pamuk"],
    correct_option: "Süt - HBSS (Hank's Balanced Salt Solution) - Tükürük",
    explanation: "Avülse dişin periodontal ligament hücre canlılığını korumak için en iyi standart HBSS'dir. Eğer yoksa süt veya hastanın kendi tükürüğü (dil altı muhafaza vb.) en iyi alternatiflerdir. Su veya kuru peçete PDL hücrelerini dakikalar içinde öldürür."
  }
];

const TOPICS = [
  "Tümü",
  "Oral Patoloji",
  "Enfeksiyöz Hastalıklar",
  "Travmatik Lezyonlar"
];

// --- COMPONENT ---
export default function QuizPage() {
  const [selectedTopic, setSelectedTopic] = useState<string>("Tümü");
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);

  // Filter questions dynamically
  const filteredQuestions = useMemo(() => {
    if (selectedTopic === "Tümü") return mockQuestions;
    return mockQuestions.filter(q => q.topic === selectedTopic);
  }, [selectedTopic]);

  // Handle Option Click
  const handleSelectOption = (questionId: string, option: string) => {
    if (isSubmitted) return; // Prevent changing answer after submission
    setUserAnswers(prev => ({
      ...prev,
      [questionId]: option
    }));
  };

  // Check if all displayed questions are answered
  const allAnswered = filteredQuestions.length > 0 && filteredQuestions.every(q => userAnswers[q.id]);

  // Reset Logic
  const handleReset = () => {
    setUserAnswers({});
    setIsSubmitted(false);
    // Smooth scroll to top naturally with browser
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    // Optionally reset questions when topic changes?
    // Let's reset the state when switching topics to prevent confusion
    handleReset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTopic]);

  // Calculations for Results Dashboard
  let correctCount = 0;
  if (isSubmitted) {
    filteredQuestions.forEach(q => {
      if (userAnswers[q.id] === q.correct_option) {
        correctCount++;
      }
    });
  }
  const totalCount = filteredQuestions.length;
  const scorePercentage = totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0;

  // Determine feedback style
  let feedbackLabel = "";
  let feedbackIcon = "📚";
  let progressColor = "#e53e3e"; // default Red
  
  if (scorePercentage >= 80) {
    feedbackLabel = "Mükemmel!";
    feedbackIcon = "🏆";
    progressColor = "#38a169"; // Green
  } else if (scorePercentage >= 60) {
    feedbackLabel = "İyi!";
    feedbackIcon = "👍";
    progressColor = "#3182ce"; // Blue
  } else if (isSubmitted) {
    feedbackLabel = "Daha fazla çalışma gerekli";
    progressColor = "#e53e3e"; // Red
  }

  return (
    <div className={styles.container}>
      
      {/* HEADER */}
      <div className={styles.header}>
        <h1 className={styles.title}>
          <FileQuestion size={36} color="#0066cc" />
          Diş Hekimliği Klinik Bilgi Testi
        </h1>
        <p className={styles.subtitle}>Teorik bilginizi ölçün ve güçlü/zayıf alanlarınızı keşfedin</p>
      </div>

      {/* TOPIC SELECTOR */}
      <div className={styles.topicSelector}>
        {TOPICS.map(topic => (
          <button
            key={topic}
            className={styles.topicBtn}
            data-active={selectedTopic === topic}
            onClick={() => setSelectedTopic(topic)}
            disabled={isSubmitted}
            style={isSubmitted ? { opacity: 0.6, cursor: 'not-allowed' } : {}}
          >
            {topic}
          </button>
        ))}
      </div>

      {filteredQuestions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#718096' }}>
          <Search size={48} style={{ opacity: 0.2, marginBottom: '1rem', display: 'inline-block' }} />
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
                    {q.options.map(option => {
                      const isSelected = selectedAnswer === option;
                      
                      // Post-Submission styling variables
                      let isCorrectOption = false;
                      let isWrongOption = false;
                      
                      if (isSubmitted) {
                        isCorrectOption = option === q.correct_option; // Always highlight the actual correct option green
                        isWrongOption = isSelected && !isCorrectAnswer; // Highlight red if user picked it but it's wrong
                      }

                      return (
                        <div 
                          key={option}
                          className={`${styles.option} ${isSubmitted ? styles.optionDisabled : ''}`}
                          data-selected={isSelected && !isSubmitted}
                          data-correct={isCorrectOption}
                          data-wrong={isWrongOption}
                          onClick={() => handleSelectOption(q.id, option)}
                        >
                          <div className={styles.optionRadio}>
                            {isCorrectOption ? <CheckCircle2 size={16} /> : isWrongOption ? <XOctagon size={16} /> : null}
                          </div>
                          <span>{option}</span>
                        </div>
                      );
                    })}
                  </div>

                  {/* EXPLANATION BOX */}
                  {isSubmitted && (
                    <div className={styles.explanation}>
                      <Info size={24} style={{ flexShrink: 0, marginTop: '2px' }} />
                      <div>
                        <strong>Açıklama:</strong>
                        <p style={{ margin: '0.25rem 0 0 0' }}>{q.explanation}</p>
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
                 Testi tamamladınız. Toplam {totalCount} soru üzerinden performansınız aşağıda gösterilmektedir.
               </p>

               <div className={styles.progressBarBg}>
                 <div className={styles.progressBarFill} style={{ width: `${scorePercentage}%`, backgroundColor: progressColor }} />
               </div>

               <div className={styles.statsGrid}>
                 <div className={styles.statItem}>
                   <div className={styles.statValue} data-color="blue">{scorePercentage}%</div>
                   <div className={styles.statLabel}>Başarı Oranı</div>
                 </div>
                 <div className={styles.statItem}>
                   <div className={styles.statValue} data-color="green">{correctCount}</div>
                   <div className={styles.statLabel}>Doğru</div>
                 </div>
                 <div className={styles.statItem}>
                   <div className={styles.statValue} data-color="red">{totalCount - correctCount}</div>
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
