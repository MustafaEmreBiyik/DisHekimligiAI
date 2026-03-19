'use client';

import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4">
      <div className="text-center space-y-6 max-w-2xl bg-white p-10 rounded-2xl shadow-xl">
        <div className="space-y-2">
          <h1 className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
            Dental Tutor AI
          </h1>
          <p className="text-gray-500 text-lg">
            Diş Hekimliği Öğrencileri İçin Yapay Zeka Destekli Eğitim Asistanı
          </p>
        </div>

        <div className="flex gap-4 justify-center pt-6">
          <Link
            href="/login"
            className="px-8 py-3 bg-blue-600 text-white rounded-full font-semibold hover:bg-blue-700 transition-all shadow-lg hover:shadow-blue-200 transform hover:-translate-y-1"
          >
            Hemen Başla
          </Link>

          <button 
            disabled
            className="px-8 py-3 bg-gray-200 text-gray-400 border border-gray-300 rounded-full font-semibold cursor-not-allowed"
          >
            Dokümantasyon (Yakında)
          </button>
        </div>

        <div className="pt-8 flex justify-center gap-6 text-sm text-gray-400">
          <span className="flex items-center gap-1">⚛️ React & Next.js</span>
          <span className="flex items-center gap-1">🚀 FastAPI Backend</span>
          <span className="flex items-center gap-1">🤖 Gemini AI</span>
        </div>
      </div>
    </div>
  );
}
