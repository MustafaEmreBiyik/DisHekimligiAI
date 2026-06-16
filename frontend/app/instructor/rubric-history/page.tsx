"use client";

import React, { useEffect, useState } from "react";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { instructorAPI, rubricVersionAPI, RubricVersionItem, InstructorQuestionBankItem } from "@/lib/api";
import {
  BookOpen, ChevronDown, ChevronUp, ClipboardList,
  GitBranch, Loader2, Plus, Save, X,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function VersionBadge({ version }: { version: number }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-semibold text-violet-700">
      v{version}
    </span>
  );
}

function VersionCard({ item, isLatest }: { item: RubricVersionItem; isLatest: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`rounded-xl border ${isLatest ? "border-violet-300 bg-violet-50" : "border-slate-200 bg-white"} overflow-hidden`}>
      <button
        onClick={() => setOpen((p) => !p)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-3">
          <VersionBadge version={item.version} />
          {isLatest && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">Güncel</span>
          )}
          <span className="text-xs text-slate-500">
            {new Date(item.created_at).toLocaleString("tr-TR")} — {item.created_by}
          </span>
          {item.change_notes && (
            <span className="hidden text-xs italic text-slate-500 sm:inline">&ldquo;{item.change_notes}&rdquo;</span>
          )}
        </div>
        {open ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>
      {open && (
        <div className="grid grid-cols-1 gap-4 border-t border-slate-200 p-4 md:grid-cols-2">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase text-slate-500">Degerlendirme Olcutleri</p>
            <p className="whitespace-pre-wrap rounded-lg border border-amber-100 bg-amber-50 p-3 text-sm text-amber-900">
              {item.rubric_guide}
            </p>
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase text-slate-500">Model Yanit</p>
            <p className="whitespace-pre-wrap rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-sm text-emerald-900">
              {item.model_answer_outline}
            </p>
          </div>
          {item.change_notes && (
            <div className="md:col-span-2">
              <p className="mb-1 text-xs font-semibold uppercase text-slate-500">Degisiklik Notu</p>
              <p className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700">{item.change_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Publish form
// ---------------------------------------------------------------------------

interface PublishFormProps {
  question: InstructorQuestionBankItem;
  onPublished: (item: RubricVersionItem) => void;
  onCancel: () => void;
}

function PublishForm({ question, onPublished, onCancel }: PublishFormProps) {
  const [rubricGuide, setRubricGuide] = useState(question.rubric_guide || "");
  const [modelAnswer, setModelAnswer] = useState(question.model_answer_outline || "");
  const [changeNotes, setChangeNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rubricGuide.trim() || !modelAnswer.trim()) {
      setError("Degerlendirme olcutleri ve model yanit zorunludur.");
      return;
    }
    setIsSaving(true); setError("");
    try {
      const item = await rubricVersionAPI.publishSnapshot(question.id, {
        rubric_guide: rubricGuide,
        model_answer_outline: modelAnswer,
        change_notes: changeNotes.trim() || undefined,
      });
      onPublished(item);
    } catch {
      setError("Rubrik versiyonu kaydedilemedi.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-violet-200 bg-violet-50 p-5">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-violet-800">Yeni Rubrik Versiyonu Yayinla</h3>
        <button type="button" onClick={onCancel} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
      </div>
      {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Degerlendirme Olcutleri *</label>
          <textarea rows={5} value={rubricGuide} onChange={(e) => setRubricGuide(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Model Yanit *</label>
          <textarea rows={5} value={modelAnswer} onChange={(e) => setModelAnswer(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none" />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Degisiklik Notu (isteğe bagli)</label>
        <input type="text" value={changeNotes} onChange={(e) => setChangeNotes(e.target.value)}
          placeholder="Yapilan degisikligi kısaca aciklayin..."
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none" />
      </div>
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
          Iptal
        </button>
        <button type="submit" disabled={isSaving}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50">
          {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          Yayinla
        </button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function RubricHistoryPage() {
  const [questions, setQuestions] = useState<InstructorQuestionBankItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedQ, setSelectedQ] = useState<InstructorQuestionBankItem | null>(null);
  const [versions, setVersions] = useState<RubricVersionItem[]>([]);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [showForm, setShowForm] = useState(false);

  // Only OE questions have rubrics
  const oeQuestions = questions.filter((q) => q.question_type === "OPEN_ENDED");

  useEffect(() => {
    instructorAPI.getQuestionBank()
      .then(setQuestions)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  const loadVersions = async (q: InstructorQuestionBankItem) => {
    setSelectedQ(q); setVersions([]); setShowForm(false);
    setIsLoadingVersions(true);
    try {
      const data = await rubricVersionAPI.getVersions(q.id);
      setVersions(data);
    } catch (err) { console.error(err); }
    finally { setIsLoadingVersions(false); }
  };

  const handlePublished = (item: RubricVersionItem) => {
    setVersions((prev) => [item, ...prev]);
    setShowForm(false);
  };

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">
          <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 className="flex items-center gap-3 text-3xl font-bold text-slate-900">
              <GitBranch size={32} className="text-violet-600" />
              Rubrik Versiyonlama
            </h1>
            <p className="mt-2 text-slate-500">
              Acik uclu sorular icin rubrik gecmisini goruntuleyin ve yeni versiyon yayinlayin.
            </p>
          </header>

          <div className="flex flex-col gap-6 lg:flex-row">
            {/* Question list */}
            <div className={`overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm ${selectedQ ? "hidden lg:block lg:w-72" : "w-full"}`}>
              <div className="border-b border-slate-200 bg-slate-50 p-4 font-semibold text-slate-700">
                <div className="flex items-center gap-2">
                  <BookOpen size={16} />
                  Acik Uclu Sorular ({oeQuestions.length})
                </div>
              </div>
              {isLoading ? (
                <div className="flex justify-center p-8"><Loader2 size={24} className="animate-spin text-slate-400" /></div>
              ) : oeQuestions.length === 0 ? (
                <p className="p-8 text-center text-slate-500">Acik uclu soru bulunamadi.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {oeQuestions.map((q) => (
                    <li key={q.id}
                      onClick={() => loadVersions(q)}
                      className={`cursor-pointer border-l-4 p-4 transition-colors hover:bg-violet-50 ${selectedQ?.id === q.id ? "border-violet-500 bg-violet-50" : "border-transparent"}`}>
                      <p className="line-clamp-2 text-sm font-medium text-slate-900">{q.question_text}</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{q.topic_id}</span>
                        {q.current_rubric_version != null && (
                          <VersionBadge version={q.current_rubric_version} />
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Version history panel */}
            {selectedQ && (
              <div className="flex flex-1 flex-col gap-4">
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div>
                    <p className="text-xs text-slate-500">Secili Soru</p>
                    <p className="font-semibold text-slate-900 line-clamp-1">{selectedQ.question_text}</p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => setShowForm((p) => !p)}
                      className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700">
                      <Plus size={16} /> Yeni Versiyon
                    </button>
                    <button onClick={() => { setSelectedQ(null); setVersions([]); }}
                      className="rounded-lg border border-slate-300 p-2 text-slate-500 hover:bg-slate-50 lg:hidden">
                      <X size={16} />
                    </button>
                  </div>
                </div>

                {showForm && (
                  <PublishForm
                    question={selectedQ}
                    onPublished={handlePublished}
                    onCancel={() => setShowForm(false)}
                  />
                )}

                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <ClipboardList size={16} className="text-slate-500" />
                    <h2 className="font-semibold text-slate-700">Versiyon Gecmisi ({versions.length})</h2>
                  </div>
                  {isLoadingVersions ? (
                    <div className="flex justify-center py-8"><Loader2 size={24} className="animate-spin text-slate-400" /></div>
                  ) : versions.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
                      Bu soru icin henuz rubrik versiyonu yayinlanmamis.
                    </div>
                  ) : (
                    versions.map((v, idx) => (
                      <VersionCard key={v.id} item={v} isLatest={idx === 0} />
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </InstructorRouteGuard>
  );
}
