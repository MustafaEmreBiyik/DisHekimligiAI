"use client";

/**
 * Chat Simulation Page
 * ====================
 * Core simulation interface where students interact with the virtual patient.
 * Uses Silent Evaluator Architecture - evaluation is hidden from UI.
 */

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { chatAPI, casesAPI } from "@/lib/api";
import ChatMessage from "@/components/ChatMessage";
import CaseHeader from "@/components/CaseHeader";

interface Message {
  id: string;
  role: "student" | "patient" | "system";
  content: string;
  timestamp: Date;
  metadata?: {
    interpreted_action?: string;
    score?: number;
  };
}

interface CaseInfo {
  case_id: string;
  name: string | null;
  difficulty: string | null;
  patient: {
    age: number | null;
    gender: string | null;
    chief_complaint: string | null;
  } | null;
}

export default function ChatPage() {
  const router = useRouter();
  const params = useParams();
  const caseId = params.caseId as string;
  const { user, isLoading: authLoading } = useAuth();

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [caseInfo, setCaseInfo] = useState<CaseInfo | null>(null);
  const [currentScore, setCurrentScore] = useState(0);
  const [error, setError] = useState("");
  const [isCaseFinished, setIsCaseFinished] = useState(false);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  // Load case info and start session
  useEffect(() => {
    if (user && caseId) {
      loadCaseInfo();
    }
  }, [user, caseId]);

  const loadCaseInfo = async () => {
    setIsLoading(true);
    setError("");

    try {
      // Get case details
      const caseData = await casesAPI.getCase(caseId);
      setCaseInfo(caseData);

      // Start/resume session
      const session = await casesAPI.startSession(caseId);
      setCurrentScore(session.current_score || 0);

      // Add welcome message
      const welcomeMessage: Message = {
        id: "welcome",
        role: "system",
        content: `📋 **${
          caseData.name || "Vaka"
        }** başlatıldı.\n\n🗣️ Hasta bekleme odasında. Sorularınızı sormaya başlayabilirsiniz.`,
        timestamp: new Date(),
      };
      setMessages([welcomeMessage]);

      // Add initial patient greeting
      if (caseData.patient?.chief_complaint) {
        const patientGreeting: Message = {
          id: "greeting",
          role: "patient",
          content: `Merhaba doktor. ${caseData.patient.chief_complaint}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, patientGreeting]);
      }
    } catch (err: any) {
      console.error("Failed to load case:", err);
      setError(err.response?.data?.detail || "Vaka yüklenirken hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  // Send message to AI
  const sendMessage = async () => {
    if (!inputValue.trim() || isSending || isCaseFinished) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "student",
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsSending(true);
    setError("");

    try {
      const response = await chatAPI.sendMessage(userMessage.content, caseId);

      // Add AI response
      const aiMessage: Message = {
        id: `msg-${Date.now()}-ai`,
        role: "patient",
        content: response.response_text,
        timestamp: new Date(),
        metadata: {
          interpreted_action: response.interpreted_action,
          score: response.evaluation?.score,
        },
      };

      setMessages((prev) => [...prev, aiMessage]);
      setCurrentScore(response.score || 0);

      // Check if case is finished
      if (response.is_case_finished) {
        setIsCaseFinished(true);
        const finishMessage: Message = {
          id: "finish",
          role: "system",
          content: `🎉 **Vaka Tamamlandı!**\n\nToplam Puanınız: **${response.score}**\n\nYeni bir vaka için Dashboard'a dönebilirsiniz.`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, finishMessage]);
      }
    } catch (err: any) {
      console.error("Failed to send message:", err);
      setError(
        err.response?.data?.detail ||
          "Mesaj gönderilemedi. Lütfen tekrar deneyin."
      );

      // Add error message to chat
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: "system",
        content: "⚠️ Bir hata oluştu. Lütfen tekrar deneyin.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };

  // Handle Enter key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Vaka yükleniyor...</p>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <Link
                href="/dashboard"
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="Dashboard'a Dön"
              >
                <svg
                  className="w-5 h-5 text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
              </Link>
              <h1 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                🦷 Dental Tutor AI
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-xs text-gray-500">Puan</p>
                <p className="font-bold text-blue-600">
                  {currentScore.toFixed(0)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Case Header */}
      {caseInfo && (
        <CaseHeader
          caseName={caseInfo.name}
          difficulty={caseInfo.difficulty}
          patientAge={caseInfo.patient?.age}
          chiefComplaint={caseInfo.patient?.chief_complaint}
        />
      )}

      {/* Error Banner */}
      {error && (
        <div className="max-w-4xl mx-auto px-4 py-2">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">
            {error}
          </div>
        </div>
      )}

      {/* Messages Container */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="space-y-4">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role}
                content={message.content}
                timestamp={message.timestamp}
              />
            ))}

            {/* Typing indicator */}
            {isSending && (
              <ChatMessage role="patient" content="" isTyping={true} />
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t border-gray-200 sticky bottom-0">
        <div className="max-w-4xl mx-auto px-4 py-4">
          {isCaseFinished ? (
            <div className="text-center">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all"
              >
                Dashboard'a Dön
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 7l5 5m0 0l-5 5m5-5H6"
                  />
                </svg>
              </Link>
            </div>
          ) : (
            <div className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Hastaya soru sorun veya muayene eylemleri yazın..."
                disabled={isSending}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all disabled:bg-gray-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={sendMessage}
                disabled={!inputValue.trim() || isSending}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold px-6 py-3 rounded-xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg"
              >
                {isSending ? (
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                ) : (
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                  </svg>
                )}
              </button>
            </div>
          )}
        </div>
      </footer>
    </div>
  );
}
