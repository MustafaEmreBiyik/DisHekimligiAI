"use client";

import { useState, useEffect, useCallback } from "react";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import {
  researchAPI,
  SnapshotSummary,
  SnapshotDetail,
  getApiErrorMessage,
} from "@/lib/api";

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function DetailModal({
  detail,
  onClose,
}: {
  detail: SnapshotDetail;
  onClose: () => void;
}) {
  const scoringCfg = detail.scoring_config_payload as {
    composite_weights?: Record<string, number>;
    weak_threshold_pct?: number;
  };
  const llmCfg = detail.llm_config_payload as {
    observation_window_days?: number;
    models_observed?: { provider: string; model_id: string }[];
    captured_at?: string;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold text-gray-900 truncate">{detail.label}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>
        <div className="p-5 space-y-5">
          {/* Meta */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Oluşturan</span>
              <p className="font-medium text-gray-800">{detail.created_by}</p>
            </div>
            <div>
              <span className="text-gray-500">Tarih</span>
              <p className="font-medium text-gray-800">{formatDate(detail.created_at)}</p>
            </div>
            <div>
              <span className="text-gray-500">Git commit</span>
              <p className="font-mono text-xs text-gray-700">
                {detail.git_commit_hash ?? "bilinmiyor"}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Bundle boyutu</span>
              <p className="font-medium text-gray-800">{formatBytes(detail.bundle_size_bytes)}</p>
            </div>
          </div>

          {detail.notes && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Notlar</h3>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{detail.notes}</p>
            </div>
          )}

          {/* Content counts */}
          <div className="flex gap-4">
            <div className="flex-1 bg-indigo-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-indigo-700">{detail.questions_count}</p>
              <p className="text-xs text-indigo-600">Soru</p>
            </div>
            <div className="flex-1 bg-teal-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-teal-700">{detail.cases_count}</p>
              <p className="text-xs text-teal-600">Vaka</p>
            </div>
          </div>

          {/* Scoring config */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Puanlama Konfigürasyonu</h3>
            <div className="bg-gray-50 rounded-lg p-3 space-y-1 text-sm">
              {scoringCfg.composite_weights && (
                <>
                  <div className="flex justify-between">
                    <span className="text-gray-500">MCQ Ağırlığı</span>
                    <span className="font-mono text-gray-800">
                      {((scoringCfg.composite_weights.mcq ?? 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Açık Uçlu Ağırlığı</span>
                    <span className="font-mono text-gray-800">
                      {((scoringCfg.composite_weights.oe ?? 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Vaka Ağırlığı</span>
                    <span className="font-mono text-gray-800">
                      {((scoringCfg.composite_weights.case ?? 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                </>
              )}
              {scoringCfg.weak_threshold_pct !== undefined && (
                <div className="flex justify-between border-t pt-1">
                  <span className="text-gray-500">Zayıf konu eşiği</span>
                  <span className="font-mono text-gray-800">{scoringCfg.weak_threshold_pct}%</span>
                </div>
              )}
            </div>
          </div>

          {/* LLM config */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              LLM Modelleri{" "}
              <span className="text-gray-400 font-normal">
                (son {llmCfg.observation_window_days ?? 90} gün)
              </span>
            </h3>
            {llmCfg.models_observed && llmCfg.models_observed.length > 0 ? (
              <div className="space-y-1">
                {llmCfg.models_observed.map((m, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-sm bg-gray-50 rounded px-3 py-1"
                  >
                    <span className="text-xs bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded font-medium">
                      {m.provider}
                    </span>
                    <span className="font-mono text-gray-700 text-xs">{m.model_id}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">Bu dönemde LLM etkileşim kaydı yok.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function CreateModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (s: SnapshotSummary) => void;
}) {
  const [label, setLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!label.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const snapshot = await researchAPI.createSnapshot({
        label: label.trim(),
        notes: notes.trim() || undefined,
      });
      onCreated(snapshot);
    } catch (err) {
      setError(getApiErrorMessage(err, "Snapshot oluşturulamadı."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Yeni Araştırma Snapshot'u</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Etiket <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Örn: Bahar 2026 – Yarı Dönem Snapshot"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notlar</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="İsteğe bağlı — yayın amacı, çalışma fazı, vb."
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={loading || !label.trim()}
              className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Oluşturuluyor…" : "Snapshot Oluştur"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function ResearchSnapshotsPage() {
  const [snapshots, setSnapshots] = useState<SnapshotSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [detailSnapshot, setDetailSnapshot] = useState<SnapshotDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSnapshots(await researchAPI.listSnapshots());
    } catch (err) {
      setError(getApiErrorMessage(err, "Snapshotlar yüklenemedi."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function openDetail(id: number) {
    setDetailLoading(true);
    try {
      setDetailSnapshot(await researchAPI.getSnapshot(id));
    } catch {
      /* no-op */
    } finally {
      setDetailLoading(false);
    }
  }

  function handleCreated(s: SnapshotSummary) {
    setShowCreate(false);
    setSnapshots((prev) => [s, ...prev]);
  }

  return (
    <InstructorRouteGuard>
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Araştırma Snapshot'ları</h1>
              <p className="text-sm text-gray-500 mt-0.5">
                Sistem durumunun immutable anlık görüntüleri — akademik yayın reproducibility için
              </p>
            </div>
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
            >
              + Yeni Snapshot
            </button>
          </div>

          {/* Info banner */}
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
            <strong>Ne kaydedilir?</strong> Her snapshot; aktif sorular ve rubrikler, vaka
            tanımları ve puanlama kuralları, ağırlık konfigürasyonu ve kullanılan LLM model
            kimliklerini tek bir indirilebilir JSON bundle olarak dondurur. Yayında
            &ldquo;DentAI snapshot 2026-05-31&rdquo; referansıyla bulgular yeniden üretilebilir.
          </div>

          {/* Content */}
          {loading && (
            <div className="text-center py-16 text-gray-400">Yükleniyor…</div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {!loading && !error && snapshots.length === 0 && (
            <div className="text-center py-20 text-gray-400">
              <p className="text-4xl mb-3">📸</p>
              <p className="font-medium">Henüz snapshot yok</p>
              <p className="text-sm mt-1">
                İlk araştırma snapshot&apos;unu oluşturmak için yukarıdaki butonu kullanın.
              </p>
            </div>
          )}

          {!loading && snapshots.length > 0 && (
            <div className="space-y-3">
              {snapshots.map((s) => (
                <div
                  key={s.id}
                  className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs bg-gray-100 text-gray-500 font-mono px-2 py-0.5 rounded">
                          #{s.id}
                        </span>
                        <h3 className="font-semibold text-gray-900 truncate">{s.label}</h3>
                        {s.git_commit_hash && (
                          <span className="text-xs bg-slate-100 text-slate-600 font-mono px-2 py-0.5 rounded">
                            {s.git_commit_hash}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        {formatDate(s.created_at)} · {s.created_by}
                      </p>
                      {s.notes && (
                        <p className="text-sm text-gray-600 mt-1.5 line-clamp-2">{s.notes}</p>
                      )}
                    </div>

                    <div className="flex-shrink-0 text-right text-xs text-gray-500 space-y-1">
                      <p>
                        <span className="font-medium text-gray-700">{s.questions_count}</span> soru
                      </p>
                      <p>
                        <span className="font-medium text-gray-700">{s.cases_count}</span> vaka
                      </p>
                      <p>{formatBytes(s.bundle_size_bytes)}</p>
                    </div>
                  </div>

                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => openDetail(s.id)}
                      disabled={detailLoading}
                      className="text-xs px-3 py-1.5 rounded border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Detay
                    </button>
                    <a
                      href={researchAPI.getExportUrl(s.id)}
                      download
                      className="text-xs px-3 py-1.5 rounded border border-indigo-200 text-indigo-600 hover:bg-indigo-50"
                    >
                      JSON İndir
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
      {detailSnapshot && (
        <DetailModal detail={detailSnapshot} onClose={() => setDetailSnapshot(null)} />
      )}
    </InstructorRouteGuard>
  );
}
