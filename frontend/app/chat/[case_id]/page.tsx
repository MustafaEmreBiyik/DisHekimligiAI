'use client';

/**
 * Chat Interface Page
 * ===================
 * Virtual Patient Chat - Core feature for clinical reasoning assessment.
 * Dynamic route: /chat/[case_id]
 */

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { chatAPI, feedbackAPI } from '@/lib/api';
import Link from 'next/link';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    score?: number;
    timestamp?: Date;
}

export default function ChatPage() {
    const params = useParams();
    const router = useRouter();
    const { user, isLoading: authLoading } = useAuth();
    
    const case_id = params.case_id as string;
    
    // State management
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [currentScore, setCurrentScore] = useState(0);
    const [error, setError] = useState('');
    const [sessionId, setSessionId] = useState<number | null>(null);
    
    // Feedback modal state
    const [showFeedbackModal, setShowFeedbackModal] = useState(false);
    const [feedbackRating, setFeedbackRating] = useState(0);
    const [feedbackComment, setFeedbackComment] = useState('');
    const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
    
    // Auto-scroll reference
    const messagesEndRef = useRef<HTMLDivElement>(null);
    
    // Redirect to login if not authenticated
    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);
    
    // Auto-scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);
    
    // Initial welcome message
    useEffect(() => {
        if (user) {
            setMessages([
                {
                    role: 'assistant',
                    content: '👋 Hoş geldiniz! Ben sanal hastanızım. Tanı ve tedavi sürecinizi başlatmak için eylemlerinizi yazabilirsiniz. Örnek: "Hastanın şikayetini dinliyorum" veya "Ağız içi muayene yapıyorum".',
                    timestamp: new Date()
                }
            ]);
        }
    }, [user]);
    
    // Handle message submit
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!inputMessage.trim() || isLoading) return;
        
        const userMessage = inputMessage.trim();
        setInputMessage('');
        setError('');
        
        // Add user message to UI immediately
        const newUserMessage: Message = {
            role: 'user',
            content: userMessage,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, newUserMessage]);
        
        // Show loading state
        setIsLoading(true);
        
        try {
            // Call API
            const response = await chatAPI.sendMessage(userMessage, case_id);
            
            // Capture session_id from first response (for feedback submission later)
            if (!sessionId && response.session_id) {
                setSessionId(response.session_id);
            }
            
            // Add AI response to UI
            const aiMessage: Message = {
                role: 'assistant',
                content: response.final_feedback,
                score: response.score,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, aiMessage]);
            
            // Update total score
            setCurrentScore(prev => prev + response.score);
            
        } catch (err: any) {
            console.error('Chat error:', err);
            setError(err.response?.data?.detail || 'Mesaj gönderilemedi. Lütfen tekrar deneyin.');
            
            // Add error message to chat
            const errorMessage: Message = {
                role: 'assistant',
                content: '❌ Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.',
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };
    
    // Handle feedback submission
    const handleFeedbackSubmit = async () => {
        if (feedbackRating === 0) {
            alert('Lütfen bir yıldız değerlendirmesi seçin.');
            return;
        }
        
        if (!sessionId) {
            alert('Session ID bulunamadı. Lütfen önce vakayla etkileşime geçin.');
            return;
        }
        
        setIsSubmittingFeedback(true);
        
        try {
            await feedbackAPI.submitFeedback(
                sessionId,
                case_id,
                feedbackRating,
                feedbackComment || undefined
            );
            
            // Success - redirect to dashboard
            alert('✅ Geri bildiriminiz başarıyla kaydedildi. Teşekkür ederiz!');
            router.push('/dashboard');
            
        } catch (err: any) {
            console.error('Feedback error:', err);
            alert(err.response?.data?.detail || 'Geri bildirim gönderilemedi. Lütfen tekrar deneyin.');
        } finally {
            setIsSubmittingFeedback(false);
        }
    };
    
    // Handle end case button
    const handleEndCase = () => {
        if (messages.length <= 1) {
            alert('⚠️ Henüz vakayla etkileşime geçmediniz. Lütfen önce hastanızla konuşun.');
            return;
        }
        setShowFeedbackModal(true);
    };
    
    // Loading state
    if (authLoading || !user) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Yükleniyor...</p>
                </div>
            </div>
        );
    }
    
    // Get case display name
    const getCaseName = () => {
        const caseNames: { [key: string]: string } = {
            'olp_001': 'Oral Liken Planus',
            'infectious_child_01': 'Herpes (Pediatrik)',
            'perio_001': 'Kronik Periodontitis',
            'herpes_primary_01': 'Primer Herpetik Gingivostomatitis',
            'behcet_01': 'Behçet Hastalığı',
            'syphilis_02': 'İkincil Sifiliz',
            'desquamative_01': 'Desgüamatif Gingivit'
        };
        return caseNames[case_id] || case_id;
    };
    
    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex flex-col">
            {/* Header */}
            <header className="bg-white shadow-sm border-b border-gray-100 sticky top-0 z-10">
                <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link
                            href="/dashboard"
                            className="text-gray-600 hover:text-blue-600 transition-colors"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                        </Link>
                        <div>
                            <h1 className="text-xl font-bold text-gray-900">
                                {getCaseName()}
                            </h1>
                            <p className="text-sm text-gray-500">Vaka ID: {case_id}</p>
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                        {/* End Case Button */}
                        <button
                            onClick={handleEndCase}
                            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all text-sm"
                        >
                            ✓ Vakayı Tamamla
                        </button>
                        
                        {/* Score Display */}
                        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-2 rounded-full shadow-lg">
                            <div className="text-center">
                                <p className="text-xs font-semibold">Toplam Puan</p>
                                <p className="text-2xl font-bold">{currentScore.toFixed(0)}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </header>
            
            {/* Messages Area */}
            <main className="flex-1 overflow-y-auto px-4 py-6">
                <div className="max-w-4xl mx-auto space-y-4">
                    {messages.map((msg, index) => (
                        <div
                            key={index}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[75%] rounded-2xl px-5 py-3 shadow-md ${
                                    msg.role === 'user'
                                        ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
                                        : 'bg-white text-gray-900 border border-gray-100'
                                }`}
                            >
                                {/* Role Badge */}
                                <div className="flex items-center gap-2 mb-2">
                                    <span className={`text-xs font-semibold ${
                                        msg.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                                    }`}>
                                        {msg.role === 'user' ? '👨‍⚕️ Siz' : '🤒 Hasta'}
                                    </span>
                                    {msg.score !== undefined && msg.score > 0 && (
                                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full font-semibold">
                                            +{msg.score} puan
                                        </span>
                                    )}
                                </div>
                                
                                {/* Message Content */}
                                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                                    {msg.content}
                                </p>
                                
                                {/* Timestamp */}
                                {msg.timestamp && (
                                    <p className={`text-xs mt-2 ${
                                        msg.role === 'user' ? 'text-blue-100' : 'text-gray-400'
                                    }`}>
                                        {msg.timestamp.toLocaleTimeString('tr-TR', { 
                                            hour: '2-digit', 
                                            minute: '2-digit' 
                                        })}
                                    </p>
                                )}
                            </div>
                        </div>
                    ))}
                    
                    {/* Loading Indicator */}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="bg-white text-gray-900 border border-gray-100 rounded-2xl px-5 py-3 shadow-md">
                                <div className="flex items-center gap-2">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                    <span className="text-sm text-gray-500">Hasta düşünüyor...</span>
                                </div>
                            </div>
                        </div>
                    )}
                    
                    {/* Error Display */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                            {error}
                        </div>
                    )}
                    
                    {/* Auto-scroll anchor */}
                    <div ref={messagesEndRef} />
                </div>
            </main>
            
            {/* Input Area */}
            <footer className="bg-white border-t border-gray-200 sticky bottom-0 shadow-lg">
                <div className="max-w-4xl mx-auto px-4 py-4">
                    <form onSubmit={handleSubmit} className="flex gap-3">
                        <input
                            type="text"
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            placeholder="Eylemlerinizi yazın (ör: Hastanın şikayetini dinliyorum)..."
                            disabled={isLoading}
                            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
                        />
                        <button
                            type="submit"
                            disabled={isLoading || !inputMessage.trim()}
                            className="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                        >
                            {isLoading ? (
                                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            ) : (
                                'Gönder'
                            )}
                        </button>
                    </form>
                    
                    {/* Helper Text */}
                    <p className="text-xs text-gray-500 mt-2 text-center">
                        💡 İpucu: Eylemlerinizi detaylı yazın (ör: "Oral mukoza muayenesi yapıyorum" veya "Hastanın tıbbi geçmişini sorguluyorum")
                    </p>
                </div>
            </footer>
            
            {/* Feedback Modal */}
            {showFeedbackModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
                        <h2 className="text-2xl font-bold text-gray-900 mb-4">
                            Vakayı Tamamla
                        </h2>
                        <p className="text-gray-600 mb-6">
                            Deneyiminizi değerlendirin. Geri bildiriminiz araştırmamız için çok değerlidir.
                        </p>
                        
                        {/* Star Rating */}
                        <div className="mb-6">
                            <label className="block text-sm font-semibold text-gray-700 mb-3">
                                Genel Değerlendirme *
                            </label>
                            <div className="flex gap-2 justify-center">
                                {[1, 2, 3, 4, 5].map((star) => (
                                    <button
                                        key={star}
                                        type="button"
                                        onClick={() => setFeedbackRating(star)}
                                        className="text-4xl transition-all transform hover:scale-110"
                                    >
                                        {star <= feedbackRating ? '⭐' : '☆'}
                                    </button>
                                ))}
                            </div>
                            <p className="text-center text-sm text-gray-500 mt-2">
                                {feedbackRating === 0 && 'Yıldızlara tıklayarak değerlendirin'}
                                {feedbackRating === 1 && 'Çok Kötü'}
                                {feedbackRating === 2 && 'Kötü'}
                                {feedbackRating === 3 && 'Orta'}
                                {feedbackRating === 4 && 'İyi'}
                                {feedbackRating === 5 && 'Mükemmel'}
                            </p>
                        </div>
                        
                        {/* Comment */}
                        <div className="mb-6">
                            <label className="block text-sm font-semibold text-gray-700 mb-2">
                                Yorumlarınız (Opsiyonel)
                            </label>
                            <textarea
                                value={feedbackComment}
                                onChange={(e) => setFeedbackComment(e.target.value)}
                                placeholder="Vaka hakkında düşüncelerinizi paylaşın..."
                                rows={4}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none"
                            />
                        </div>
                        
                        {/* Buttons */}
                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowFeedbackModal(false)}
                                disabled={isSubmittingFeedback}
                                className="flex-1 px-4 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                İptal
                            </button>
                            <button
                                onClick={handleFeedbackSubmit}
                                disabled={isSubmittingFeedback || feedbackRating === 0}
                                className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isSubmittingFeedback ? 'Gönderiliyor...' : 'Gönder ve Bitir'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
