"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
  Stethoscope, 
  Send, 
  AlertTriangle, 
  XOctagon, 
  CheckCircle, 
  Microscope,
  Code,
  ChevronDown,
  ChevronUp,
  Loader2
} from "lucide-react";
import styles from "./Medgemma.module.css";

// --- MOCK API ---
// Simulates the MedGemmaService feedback
const simulateMedGemmaResponse = async (scenario: string, text: string) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      let result = {
        safety_violation: false,
        is_clinically_accurate: true,
        feedback: "Klinik kararınız makul görünüyor ve kurallara uygundur.",
        missing_critical_info: [] as string[]
      };

      const lowerText = text.toLowerCase();

      if (scenario === "Penisilin Alerjisi") {
        if (lowerText.includes("penisilin") || lowerText.includes("amoksisilin") || lowerText.includes("augmentin") || lowerText.includes("amoklavin")) {
          result = {
            safety_violation: true,
            is_clinically_accurate: false,
            feedback: "Hastanın penisilin alerjisi (anafilaksi) öyküsü bulunmasına rağmen penisilin grubu antibiyotik (Amoksisilin vb.) reçete ettiniz. Bu durum ölümcül anafilaksiye yol açabilir.",
            missing_critical_info: ["Alternatif antibiyotik (Klindamisin, Eritromisin veya Makrolid grubu) düşünülmeli."]
          };
        } else if (lowerText.includes("klindamisin") || lowerText.includes("makrolid")) {
          result = {
            safety_violation: false,
            is_clinically_accurate: true,
            feedback: "Penisilin alerjisi olan hastada doğru antibiyotik tercihinde bulundunuz. Ancak operatif müdahale önceliği de değerlendirilmeliydi.",
            missing_critical_info: ["Absenin cerrahi drenaj gerekliliği."]
          };
        } else {
          result = {
            safety_violation: false,
            is_clinically_accurate: false,
            feedback: "Yüzde şişlik (abse) varlığı nedeniyle sadece semptomatik veya yetersiz bir müdahale önerdiniz.",
            missing_critical_info: ["Abse için uygun antibiyotik önerisi (Örn: Klindamisin)", "Lokal drenaj düşünülmesi"]
          };
        }
      } 
      else if (scenario === "Diyabetik Hasta") {
        if (lowerText.includes("çekim") && !lowerText.includes("hba1c") && !lowerText.includes("şeker")) {
           result = {
            safety_violation: true,
            is_clinically_accurate: false,
            feedback: "Kontrolsüz diyabet varlığında (HbA1c 9.5) agresif cerrahi girişim yapılamaz. Ciddi enfeksiyon ve iyileşmeme riski mevcuttur.",
            missing_critical_info: ["Hastanın endokrinoloji konsültasyonuna yönlendirilmesi", "Glisemik kontrolün sağlanması", "Proflaktik antibiyotik başlanması"]
          };
        } else {
           result = {
            safety_violation: false,
            is_clinically_accurate: true,
            feedback: "Hastanın diyabet yükünü göz önüne alarak nispeten güvenli bir yaklaşım seçtiniz.",
            missing_critical_info: ["Rutin kan şekeri takibinin operasyon gününde de yapılması."]
          };
        }
      }
      else {
        // Fallback generic error
        if (lowerText.length < 15) {
          result = {
            safety_violation: false,
            is_clinically_accurate: false,
            feedback: "Eksik veya yetersiz bir klinik beyanda bulundunuz. Lütfen ne reçete edeceğinizi veya hangi prosedürü uygulayacağınızı net belirtin.",
            missing_critical_info: ["Tam bir anamnez öyküsü", "Spesifik tedavi kararı"]
          };
        }
      }

      resolve(result);
    }, 2000);
  });
};

// --- TYPES ---
interface Scenario {
  id: string;
  title: string;
  desc: string;
}

interface ValidationResult {
  safety_violation: boolean;
  is_clinically_accurate: boolean;
  feedback: string;
  missing_critical_info: string[];
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string; // Used for raw display
  validationResult?: ValidationResult; // Populated if Assistant
}

// --- COMPONENTS ---
export default function MedgemmaPage() {
  const [activeScenario, setActiveScenario] = useState("Penisilin Alerjisi");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scenarios: Scenario[] = [
    { id: "Penisilin Alerjisi", title: "Penisilin Alerjisi", desc: "12 Y - Abse - Penisilin Anafilaksisi" },
    { id: "Diyabetik Hasta", title: "Diyabetik Hasta", desc: "60 Y - Tip 2 Diyabet (HbA1c: 9.5) - İyileşmeyen Yara" },
    { id: "Hamilelik (1. Trimester)", title: "Hamilelik (1. Trimester)", desc: "28 Y - 10 Hafta Hamile - Diş Eti Kanaması" },
    { id: "Oral Liken Planus", title: "Oral Liken Planus", desc: "45 Y - Ağızda Beyaz Çizgiler ve Acı Hissi" },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim()
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const resultObj = await simulateMedGemmaResponse(activeScenario, userMessage.content);
      const validationResult = resultObj as ValidationResult;
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: JSON.stringify(validationResult, null, 2),
        validationResult
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Switch scenario (reset conversation)
  const handleScenarioSelect = (id: string) => {
    setActiveScenario(id);
    setMessages([]);
  };

  return (
    <div className={styles.container}>
      
      {/* LEFT COLUMN: Scenarios */}
      <div className={styles.scenarioPanel}>
        <div className={styles.scenarioHeader}>
          <Microscope size={28} color="#0066cc" />
          Test Senaryosu Seç
        </div>
        <p style={{ color: '#718096', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
          Modeli test etmek için bir vaka senaryosu seçin.
        </p>

        <div className={styles.scenarioList}>
          {scenarios.map((s) => (
            <div 
              key={s.id}
              className={styles.scenarioCard}
              data-active={activeScenario === s.id}
              onClick={() => handleScenarioSelect(s.id)}
            >
              <div className={styles.scenarioTitle}>{s.title}</div>
              <div className={styles.scenarioSubtitle}>{s.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT COLUMN: Console */}
      <div className={styles.consolePanel}>
        <div className={styles.consoleHeader}>
          <Stethoscope size={28} color="#2b6cb0" />
          Doğrulayıcı Konsolu ({activeScenario})
        </div>

        <div className={styles.messageArea}>
          {messages.length === 0 && !isLoading && (
            <div style={{ textAlign: 'center', color: '#a0aec0', marginTop: 'auto', marginBottom: 'auto' }}>
              <Stethoscope size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
              <p>Simülasyona başlamak için aşağıdaki alana klinik kararınızı yazın.</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={styles.messageRow} data-role={msg.role}>
              {msg.role === "user" ? (
                <div className={styles.userBubble}>{msg.content}</div>
              ) : (
                <FeedbackCard validationResult={msg.validationResult!} rawJson={msg.content} />
              )}
            </div>
          ))}

          {isLoading && (
            <div className={styles.loadingIndicator}>
              <Loader2 className={styles.spinner} size={20} color="#0066cc" />
              MedGemma kuralları denetliyor...
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Sticky Input Bar */}
        <div className={styles.inputArea}>
          <textarea 
            className={styles.inputField}
            placeholder="Klinik kararınızı veya reçetenizi yazın..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
          />
          <button 
            className={styles.sendBtn} 
            onClick={handleSend} 
            disabled={!input.trim() || isLoading}
          >
            <Send size={20} />
          </button>
        </div>
      </div>

    </div>
  );
}

// --- SUB_COMPONENT: Feedback Card ---
function FeedbackCard({ validationResult, rawJson }: { validationResult: ValidationResult, rawJson: string }) {
  const [showRaw, setShowRaw] = useState(false);

  let themeClass = styles.themeSuccess;
  let Icon = CheckCircle;
  let titleText = "Klinik Olarak Doğru";

  if (validationResult.safety_violation) {
    themeClass = styles.themeViolation;
    Icon = XOctagon;
    titleText = "GÜVENLİK İHLALİ TESPİT EDİLDİ";
  } else if (!validationResult.is_clinically_accurate) {
    themeClass = styles.themeWarning;
    Icon = AlertTriangle;
    titleText = "Klinik Hata / Eksik";
  }

  return (
    <div className={`${styles.feedbackCard} ${themeClass}`}>
      <div className={styles.feedbackHeader}>
        <Icon size={24} />
        <span>{titleText}</span>
      </div>
      
      <div className={styles.feedbackBody}>
        <div className={styles.feedbackLabel}>Analiz:</div>
        <div className={styles.feedbackText}>{validationResult.feedback}</div>

        {validationResult.missing_critical_info && validationResult.missing_critical_info.length > 0 && (
          <>
            <div className={styles.feedbackLabel}>Eksik Bırakılanlar:</div>
            <ul className={styles.missingList}>
              {validationResult.missing_critical_info.map((info, idx) => (
                <li key={idx}>{info}</li>
              ))}
            </ul>
          </>
        )}

        {/* Collapsible Accordion */}
        <div className={styles.accordion}>
          <button className={styles.accordionBtn} onClick={() => setShowRaw(!showRaw)}>
            <Code size={16} />
            Ham JSON Verisi
            {showRaw ? <ChevronUp size={16} style={{marginLeft: 'auto'}} /> : <ChevronDown size={16} style={{marginLeft: 'auto'}} />}
          </button>
          
          {showRaw && (
            <div className={styles.rawJson}>
              {rawJson}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
