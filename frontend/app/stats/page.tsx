'use client';

import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { analyticsAPI } from '@/lib/api';

export default function StatsPage() {
    const { user, isLoading } = useAuth();
    const router = useRouter();
    const [downloading, setDownloading] = useState<string | null>(null);

    useEffect(() => {
        if (!isLoading && !user) {
            router.push('/login');
        }
    }, [user, isLoading, router]);

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Yükleniyor...</p>
                </div>
            </div>
        );
    }

    if (!user) {
        return null;
    }

    const handleDownload = async (type: 'actions' | 'feedback' | 'sessions') => {
        setDownloading(type);
        try {
            if (type === 'actions') {
                await analyticsAPI.downloadActionsCSV();
            } else if (type === 'feedback') {
                await analyticsAPI.downloadFeedbackCSV();
            } else if (type === 'sessions') {
                await analyticsAPI.downloadSessionsCSV();
            }
        } catch (error) {
            console.error('Download error:', error);
            alert('İndirme sırasında bir hata oluştu. Lütfen tekrar deneyin.');
        } finally {
            setDownloading(null);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-12 px-4">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="text-blue-600 hover:text-blue-800 font-medium mb-4 flex items-center gap-2 transition-colors"
                    >
                        ← Panele Dön
                    </button>
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">
                        📊 Araştırma Verileri
                    </h1>
                    <p className="text-gray-600">
                        Pilot çalışma verilerini CSV formatında indirin
                    </p>
                </div>

                {/* Export Cards */}
                <div className="grid gap-6 md:grid-cols-3">
                    {/* Actions CSV */}
                    <div className="bg-white rounded-2xl shadow-lg p-6 border-2 border-gray-100 hover:border-blue-300 transition-all">
                        <div className="text-4xl mb-4">🎬</div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                            Eylem Kayıtları
                        </h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Tüm öğrenci eylemleri, AI cevapları ve oturum metadataları
                        </p>
                        <button
                            onClick={() => handleDownload('actions')}
                            disabled={downloading !== null}
                            className="w-full px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {downloading === 'actions' ? (
                                <span className="flex items-center justify-center gap-2">
                                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                    İndiriliyor...
                                </span>
                            ) : (
                                '⬇️ İndir (CSV)'
                            )}
                        </button>
                    </div>

                    {/* Feedback CSV */}
                    <div className="bg-white rounded-2xl shadow-lg p-6 border-2 border-gray-100 hover:border-green-300 transition-all">
                        <div className="text-4xl mb-4">💬</div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                            Geri Bildirimler
                        </h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Öğrenci değerlendirmeleri ve yorumları (yıldız puanları dahil)
                        </p>
                        <button
                            onClick={() => handleDownload('feedback')}
                            disabled={downloading !== null}
                            className="w-full px-4 py-3 bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {downloading === 'feedback' ? (
                                <span className="flex items-center justify-center gap-2">
                                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                    İndiriliyor...
                                </span>
                            ) : (
                                '⬇️ İndir (CSV)'
                            )}
                        </button>
                    </div>

                    {/* Sessions CSV */}
                    <div className="bg-white rounded-2xl shadow-lg p-6 border-2 border-gray-100 hover:border-purple-300 transition-all">
                        <div className="text-4xl mb-4">📝</div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                            Oturum Özeti
                        </h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Tüm öğrenci oturumları ve zaman damgaları
                        </p>
                        <button
                            onClick={() => handleDownload('sessions')}
                            disabled={downloading !== null}
                            className="w-full px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {downloading === 'sessions' ? (
                                <span className="flex items-center justify-center gap-2">
                                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                    İndiriliyor...
                                </span>
                            ) : (
                                '⬇️ İndir (CSV)'
                            )}
                        </button>
                    </div>
                </div>

                {/* Info Box */}
                <div className="mt-8 bg-blue-50 border-2 border-blue-200 rounded-2xl p-6">
                    <h3 className="text-lg font-bold text-blue-900 mb-2 flex items-center gap-2">
                        ℹ️ Veri Yapısı Bilgisi
                    </h3>
                    <ul className="text-sm text-blue-800 space-y-2">
                        <li>
                            <strong>Eylem Kayıtları:</strong> Her satır bir chat mesajını temsil eder (student_id, case_id, action, ai_response, message_number, session_id, timestamp)
                        </li>
                        <li>
                            <strong>Geri Bildirimler:</strong> Vaka sonunda toplanan değerlendirmeler (session_id, case_id, rating 1-5, comment, timestamp)
                        </li>
                        <li>
                            <strong>Oturum Özeti:</strong> Her vaka denemesinin meta bilgileri (session_id, student_id, case_id, start_time, end_time, total_messages)
                        </li>
                    </ul>
                </div>

                {/* Research Note */}
                <div className="mt-6 bg-gradient-to-r from-amber-50 to-yellow-50 border-2 border-amber-200 rounded-2xl p-6">
                    <h3 className="text-lg font-bold text-amber-900 mb-2 flex items-center gap-2">
                        🔬 Araştırma Notu
                    </h3>
                    <p className="text-sm text-amber-800">
                        Bu veriler akademik araştırma amaçlıdır. Tüm öğrenci kimlikleri anonimleştirilmiştir. 
                        Veriler yalnızca dental eğitim müfredatının geliştirilmesi için kullanılacaktır.
                    </p>
                </div>
            </div>
        </div>
    );
}
