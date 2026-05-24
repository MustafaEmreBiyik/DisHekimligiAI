"use client";

import React, { useEffect, useState } from "react";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { instructorAPI, GradingQueueItem } from "@/lib/api";
import {
  Bot, CheckCircle2, ChevronRight, ClipboardList,
  Loader2, Sparkles, ThumbsDown, ThumbsUp, X,
} from "lucide-react";

interface AIDraft {
  answer_id: number;
  suggested_score: number;
  rationale: string;
  scored_at: string;
  max_score: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function requestAiScore(answerId: number): Promise<AIDraft> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const resp = await fetch(`${API_BASE}/api/quiz/instructor/answers/${answerId}/ai-score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error((err as Record<string,string>).detail || `AI scoring failed (${resp.status})`);
  }
  return resp.json() as Promise<AIDraft>;
}

export default function GradingQueuePage() {
  const [queue, setQueue] = useState<GradingQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<GradingQueueItem | null>(null);
  const [score, setScore] = useState<number>(0);
  const [feedback, setFeedback] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [aiDraft, setAiDraft] = useState<AIDraft | null>(null);
  const [isRequestingAi, setIsRequestingAi] = useState(false);
  const [aiError, setAiError] = useState("");

  useEffect(() => { loadQueue(); }, []);

  const loadQueue = async () => {
    setIsLoading(true);
    try { const data = await instructorAPI.getGradingQueue(); setQueue(data); }
    catch (err) { console.error(err); }
    finally { setIsLoading(false); }
  };

  const handleSelect = (item: GradingQueueItem) => {
    setSelectedItem(item); setScore(item.max_score);
    setFeedback(""); setAiDraft(null); setAiError("");
  };
  const handleClose = () => { setSelectedItem(null); setAiDraft(null); setAiError(""); };

  const handleSubmit = async (publish: boolean) => {
    if (!selectedItem) return;
    setIsSubmitting(true);
    try {
      await instructorAPI.submitGrade(selectedItem.answer_id, { instructor_score: score, instructor_feedback: feedback, publish });
      setSelectedItem(null); setAiDraft(null); await loadQueue();
    } catch (err) { console.error(err); }
    finally { setIsSubmitting(false); }
  };

  const handleRequestAiScore = async () => {
    if (!selectedItem) return;
    setIsRequestingAi(true); setAiError(""); setAiDraft(null);
    try { const draft = await requestAiScore(selectedItem.answer_id); setAiDraft(draft); }
    catch (err: unknown) { setAiError(err instanceof Error ? err.message : "AI puanlama istegi basarisiz."); }
    finally { setIsRequestingAi(false); }
  };

  const handleAcceptAiDraft = () => {
    if (!aiDraft) return;
    setScore(Math.round(aiDraft.suggested_score)); setFeedback(aiDraft.rationale);
  };

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">
          <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 className="flex items-center gap-3 text-3xl font-bold text-slate-900">
              <ClipboardList size={32} className="text-blue-600" />
              Degerlendirme Kuyrugu
            </h1>
          </header>

          <div className="flex flex-col gap-6 lg:flex-row">
            <div className={`flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm ${selectedItem ? "hidden lg:block lg:w-1/3" : "w-full"}`}>
              <div className="border-b border-slate-200 bg-slate-50 p-4 font-semibold text-slate-700">
                Bekleyen Yanitlar ({queue.length})
              </div>
              {isLoading ? (
                <div className="flex justify-center p-8 text-slate-400"><Loader2 size={24} className="animate-spin" /></div>
              ) : queue.length === 0 ? (
                <div className="p-8 text-center text-slate-500">Bekleyen yanit bulunmuyor.</div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {queue.map((item) => (
                    <li key={item.answer_id}
                      className={`cursor-pointer border-l-4 p-4 transition-colors hover:bg-blue-50 ${selectedItem?.answer_id === item.answer_id ? "border-blue-500 bg-blue-50" : "border-transparent"}`}
                      onClick={() => handleSelect(item)}>
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="line-clamp-1 text-sm font-medium text-slate-900">{item.question_text}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {item.submitted_at ? new Date(item.submitted_at).toLocaleDateString("tr-TR") : "-"}
                          </p>
                        </div>
                        <ChevronRight size={16} className="text-slate-400" />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {selectedItem && (
              <div className="flex h-full flex-[2] flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 p-4">
                  <h2 className="font-semibold text-slate-800">Yanit Degerlendirme</h2>
                  <button onClick={handleClose} className="text-slate-400 hover:text-slate-600 lg:hidden"><X size={20} /></button>
                </div>

                <div className="flex-1 space-y-6 overflow-y-auto p-6">
                  <div>
                    <h3 className="mb-2 text-xs font-semibold uppercase text-slate-500">Soru</h3>
                    <p className="rounded-lg border border-slate-100 bg-slate-50 p-4">{selectedItem.question_text}</p>
                  </div>
                  <div>
                    <h3 className="mb-2 text-xs font-semibold uppercase text-slate-500">Ogrenci Yaniti</h3>
                    <p className="whitespace-pre-wrap rounded-lg border border-blue-100 bg-blue-50 p-4">{selectedItem.student_response}</p>
                  </div>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="rounded-lg border border-amber-100 bg-amber-50 p-4">
                      <h3 className="mb-1 text-xs font-bold uppercase text-amber-800">Degerlendirme Olcutleri</h3>
                      <p className="whitespace-pre-wrap text-sm text-amber-900">{selectedItem.rubric_guide || "Belirtilmemis."}</p>
                    </div>
                    <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-4">
                      <h3 className="mb-1 text-xs font-bold uppercase text-emerald-800">Model Yanit</h3>
                      <p className="whitespace-pre-wrap text-sm text-emerald-900">{selectedItem.model_answer_outline || "Belirtilmemis."}</p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-violet-200 bg-violet-50 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Bot className="h-5 w-5 text-violet-600" />
                        <span className="font-semibold text-violet-800">AI Puanlama Onerisi</span>
                        <span className="rounded-full bg-violet-200 px-2 py-0.5 text-xs text-violet-700">Taslak</span>
                      </div>
                      <button type="button" onClick={handleRequestAiScore} disabled={isRequestingAi}
                        className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50">
                        {isRequestingAi ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                        {isRequestingAi ? "AI Puanliyor..." : "AI Puan Iste"}
                      </button>
                    </div>
                    {aiError && <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{aiError}</p>}
                    {aiDraft && (
                      <div className="mt-4 space-y-3">
                        <div className="flex flex-wrap items-center gap-4">
                          <div className="rounded-xl border border-violet-300 bg-white px-5 py-3 text-center">
                            <p className="text-xs text-slate-500">AI Oneri</p>
                            <p className="text-2xl font-bold text-violet-700">{aiDraft.suggested_score}<span className="text-sm font-normal text-slate-500">/{aiDraft.max_score}</span></p>
                          </div>
                          <div className="flex-1">
                            <p className="text-xs font-semibold uppercase text-slate-500">Gerekce</p>
                            <p className="mt-1 text-sm text-slate-700">{aiDraft.rationale}</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button type="button" onClick={handleAcceptAiDraft}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700">
                            <ThumbsUp className="h-4 w-4" /> Kabul Et
                          </button>
                          <button type="button" onClick={() => setAiDraft(null)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                            <ThumbsDown className="h-4 w-4" /> Reddet
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-slate-200 pt-6">
                    <h3 className="mb-4 text-lg font-bold text-slate-900">Puanlama</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Puan (Maks: {selectedItem.max_score})</label>
                        <input type="number" min={0} max={selectedItem.max_score} value={score}
                          onChange={(e) => setScore(Number(e.target.value))}
                          className="w-full rounded-md border border-slate-300 px-3 py-2 sm:w-32" />
                      </div>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">Geri Bildirim</label>
                        <textarea rows={4} value={feedback} onChange={(e) => setFeedback(e.target.value)}
                          placeholder="Ogrenciye geri bildirim..."
                          className="w-full rounded-md border border-slate-300 px-3 py-2" />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3 rounded-b-2xl border-t border-slate-200 bg-slate-50 p-4">
                  <button onClick={() => handleSubmit(false)} disabled={isSubmitting}
                    className="rounded-lg border border-slate-300 px-4 py-2 font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50">
                    Taslak Kaydet
                  </button>
                  <button onClick={() => handleSubmit(true)} disabled={isSubmitting}
                    className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                    {isSubmitting ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
                    Yayinla
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </InstructorRouteGuard>
  );
}
