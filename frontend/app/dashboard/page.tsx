'use client';

/**
 * Dashboard Page
 * ==============
 * Protected dashboard with case selection for authenticated students.
 */

import React, { useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function DashboardPage() {
    const router = useRouter();
    const { user, logout, isLoading } = useAuth();

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!isLoading && !user) {
            router.push('/login');
        }
    }, [user, isLoading, router]);

    if (isLoading || !user) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Yükleniyor...</p>
                </div>
            </div>
        );
    }

    const cases = [
        {
            id: 'olp_001',
            title: 'Oral Liken Planus',
            description: 'Kronik mukokütanöz hastalık - tanı ve tedavi yaklaşımları',
            difficulty: 'Orta',
            icon: '🔬',
            color: 'from-blue-500 to-blue-600',
        },
        {
            id: 'infectious_child_01',
            title: 'Herpes (Pediatrik)',
            description: 'Çocuk hastada viral enfeksiyon yönetimi',
            difficulty: 'Kolay',
            icon: '👶',
            color: 'from-purple-500 to-purple-600',
        },
    ];

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
            {/* Header */}
            <header className="bg-white shadow-sm border-b border-gray-100">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                                🦷 Dental Tutor AI
                            </h1>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="text-right">
                                <p className="text-sm text-gray-500">Hoş geldin,</p>
                                <p className="font-semibold text-gray-900">{user.name}</p>
                            </div>
                            <button
                                onClick={logout}
                                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors text-sm font-medium"
                            >
                                Çıkış Yap
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                {/* Welcome Section */}
                <div className="mb-12">
                    <h2 className="text-4xl font-bold text-gray-900 mb-3">
                        Hoş geldin, {user.name} 👋
                    </h2>
                    <p className="text-lg text-gray-600 mb-2">
                        Öğrenci ID: <span className="font-mono font-semibold">{user.student_id}</span>
                    </p>
                    <p className="text-gray-600">
                        Aşağıdaki vakalardan birini seçerek eğitiminize başlayabilirsiniz.
                    </p>
                </div>

                {/* Cases Section */}
                <div className="mb-8">
                    <h3 className="text-2xl font-bold text-gray-900 mb-6">
                        📁 Mevcut Vakalar
                    </h3>

                    <div className="grid md:grid-cols-2 gap-6">
                        {cases.map((caseItem) => (
                            <Link
                                key={caseItem.id}
                                href={`/chat/${caseItem.id}`}
                                className="group bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden border border-gray-100 hover:border-blue-200 transform hover:-translate-y-1"
                            >
                                <div className={`h-2 bg-gradient-to-r ${caseItem.color}`}></div>
                                <div className="p-6">
                                    <div className="flex items-start gap-4">
                                        <div className="text-5xl">{caseItem.icon}</div>
                                        <div className="flex-1">
                                            <h4 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                                                {caseItem.title}
                                            </h4>
                                            <p className="text-gray-600 text-sm mb-4">
                                                {caseItem.description}
                                            </p>
                                            <div className="flex items-center gap-3">
                                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${caseItem.difficulty === 'Kolay'
                                                        ? 'bg-green-100 text-green-800'
                                                        : 'bg-yellow-100 text-yellow-800'
                                                    }`}>
                                                    {caseItem.difficulty}
                                                </span>
                                                <span className="text-sm text-gray-500">
                                                    Vaka ID: {caseItem.id}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="mt-4 pt-4 border-t border-gray-100">
                                        <p className="text-blue-600 font-semibold text-sm group-hover:text-blue-700 flex items-center gap-2">
                                            Vakayı Başlat
                                            <svg className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                            </svg>
                                        </p>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                </div>

                {/* Quick Actions */}
                <div className="mb-8">
                    <h3 className="text-2xl font-bold text-gray-900 mb-6">
                        ⚡ Hızlı Erişim
                    </h3>

                    <div className="grid md:grid-cols-3 gap-4">
                        <Link
                            href="/stats"
                            className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-all border border-gray-100 hover:border-purple-200"
                        >
                            <div className="text-3xl mb-3">📊</div>
                            <h4 className="font-bold text-gray-900 mb-1">İstatistiklerim</h4>
                            <p className="text-sm text-gray-600">Performans analizi ve ilerleme</p>
                        </Link>

                        <Link
                            href="/cases"
                            className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-all border border-gray-100 hover:border-purple-200"
                        >
                            <div className="text-3xl mb-3">📚</div>
                            <h4 className="font-bold text-gray-900 mb-1">Tüm Vakalar</h4>
                            <p className="text-sm text-gray-600">Vaka kütüphanesine göz at</p>
                        </Link>

                        <Link
                            href="/profile"
                            className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-all border border-gray-100 hover:border-purple-200"
                        >
                            <div className="text-3xl mb-3">👤</div>
                            <h4 className="font-bold text-gray-900 mb-1">Profilim</h4>
                            <p className="text-sm text-gray-600">Hesap ayarları ve bilgileri</p>
                        </Link>
                    </div>
                </div>

                {/* Info Banner */}
                <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-8 rounded-2xl shadow-xl">
                    <div className="flex items-start gap-4">
                        <div className="text-4xl">💡</div>
                        <div className="flex-1">
                            <h3 className="text-2xl font-bold mb-3">
                                Nasıl Çalışır?
                            </h3>
                            <div className="space-y-2 text-blue-50">
                                <p>✓ Bir vaka seçin ve yapay zeka destekli sohbeti başlatın</p>
                                <p>✓ Tanı ve tedavi yaklaşımınızı açıklayın</p>
                                <p>✓ Gerçek zamanlı geri bildirim alın ve öğrenin</p>
                                <p>✓ İlerlemenizi takip edin ve performansınızı geliştirin</p>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
