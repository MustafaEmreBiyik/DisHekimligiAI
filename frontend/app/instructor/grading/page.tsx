"use client";

import React, { useEffect, useState } from "react";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { instructorAPI, GradingQueueItem } from "@/lib/api";
import { ClipboardList, CheckCircle2, ChevronRight, X, Loader2 } from "lucide-react";

export default function GradingQueuePage() {
  const [queue, setQueue] = useState<GradingQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<GradingQueueItem | null>(null);
  const [score, setScore] = useState<number>(0);
  const [feedback, setFeedback] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    setIsLoading(true);
    try {
      const data = await instructorAPI.getGradingQueue();
      setQueue(data);
    } catch (err) {
      console.error("Failed to load grading queue", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = (item: GradingQueueItem) => {
    setSelectedItem(item);
    setScore(item.max_score);
    setFeedback("");
  };

  const handleClose = () => {
    setSelectedItem(null);
  };

  const handleSubmit = async (publish: boolean) => {
    if (!selectedItem) return;
    setIsSubmitting(true);
    try {
      await instructorAPI.submitGrade(selectedItem.answer_id, {
        instructor_score: score,
        instructor_feedback: feedback,
        publish
      });
      setSelectedItem(null);
      await loadQueue();
    } catch (err) {
      console.error("Failed to submit grade", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">
          <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <ClipboardList size={32} className="text-blue-600" />
              Değerlendirme Kuyruğu
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Öğrencilerin açık uçlu yanıtlarını değerlendirin ve puanlayın.
            </p>
          </header>

          <div className="flex flex-col lg:flex-row gap-6">
            {/* QUEUE LIST */}
            <div className={`flex-1 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden ${selectedItem ? 'hidden lg:block lg:w-1/3' : 'w-full'}`}>
              <div className="p-4 border-b border-slate-200 bg-slate-50 font-semibold text-slate-700">
                Bekleyen Yanıtlar ({queue.length})
              </div>
              {isLoading ? (
                <div className="p-8 flex justify-center text-slate-400">
                  <Loader2 size={24} className="animate-spin" />
                </div>
              ) : queue.length === 0 ? (
                <div className="p-8 text-center text-slate-500">
                  Bekleyen yanıt bulunmuyor.
                </div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {queue.map(item => (
                    <li 
                      key={item.answer_id}
                      className={`p-4 cursor-pointer hover:bg-blue-50 transition-colors ${selectedItem?.answer_id === item.answer_id ? 'bg-blue-50 border-l-4 border-blue-500' : 'border-l-4 border-transparent'}`}
                      onClick={() => handleSelect(item)}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="text-sm font-medium text-slate-900 line-clamp-1">{item.question_text}</p>
                          <p className="text-xs text-slate-500 mt-1">Gönderim: {item.submitted_at ? new Date(item.submitted_at).toLocaleDateString('tr-TR') : '-'}</p>
                        </div>
                        <ChevronRight size={16} className="text-slate-400" />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* DETAIL VIEW */}
            {selectedItem && (
              <div className="flex-[2] rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col h-full">
                <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                  <h2 className="font-semibold text-slate-800">Yanıt Değerlendirme</h2>
                  <button onClick={handleClose} className="text-slate-400 hover:text-slate-600 lg:hidden">
                    <X size={20} />
                  </button>
                </div>
                
                <div className="p-6 space-y-6 flex-1 overflow-y-auto">
                  {/* Question & Answer */}
                  <div>
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Soru</h3>
                    <p className="text-slate-900 bg-slate-50 p-4 rounded-lg border border-slate-100">{selectedItem.question_text}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Öğrenci Yanıtı</h3>
                    <p className="text-slate-900 bg-blue-50 p-4 rounded-lg border border-blue-100 whitespace-pre-wrap">
                      {selectedItem.student_response}
                    </p>
                  </div>

                  {/* Rubric */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-amber-50 p-4 rounded-lg border border-amber-100">
                      <h3 className="text-xs font-bold text-amber-800 uppercase mb-1">Değerlendirme Ölçütleri</h3>
                      <p className="text-sm text-amber-900 whitespace-pre-wrap">{selectedItem.rubric_guide || "Ölçüt belirtilmemiş."}</p>
                    </div>
                    <div className="bg-emerald-50 p-4 rounded-lg border border-emerald-100">
                      <h3 className="text-xs font-bold text-emerald-800 uppercase mb-1">Beklenen Yanıt Özeti</h3>
                      <p className="text-sm text-emerald-900 whitespace-pre-wrap">{selectedItem.model_answer_outline || "Model yanıt belirtilmemiş."}</p>
                    </div>
                  </div>

                  {/* Grading Form */}
                  <div className="border-t border-slate-200 pt-6 mt-6">
                    <h3 className="text-lg font-bold text-slate-900 mb-4">Puanlama ve Geri Bildirim</h3>
                    
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                          Puan (Maks: {selectedItem.max_score})
                        </label>
                        <input 
                          type="number" 
                          min={0}
                          max={selectedItem.max_score}
                          value={score}
                          onChange={(e) => setScore(Number(e.target.value))}
                          className="w-full sm:w-32 px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                          Geri Bildirim
                        </label>
                        <textarea 
                          rows={4}
                          value={feedback}
                          onChange={(e) => setFeedback(e.target.value)}
                          placeholder="Öğrenciye iletilecek geri bildirimi buraya yazınız..."
                          className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3 rounded-b-2xl">
                  <button 
                    onClick={() => handleSubmit(false)}
                    disabled={isSubmitting}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 font-medium transition-colors disabled:opacity-50"
                  >
                    Taslak Kaydet
                  </button>
                  <button 
                    onClick={() => handleSubmit(true)}
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                  >
                    {isSubmitting ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
                    Yayınla
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
