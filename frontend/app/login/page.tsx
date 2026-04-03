"use client";

/**
 * Login Page
 * ==========
 * Unified authentication page for all user roles.
 * Role-based redirect destination is determined by the backend, not the client.
 */

import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AppUserRole } from "@/lib/api";

function getPostLoginPath(role: AppUserRole): string {
  if (role === "instructor") return "/instructor/dashboard";
  if (role === "admin") return "/admin/dashboard";
  return "/dashboard";
}

export default function LoginPage() {
  const router = useRouter();
  const { login, token, user, isLoading } = useAuth();

  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect away if already authenticated
  useEffect(() => {
    if (!isLoading && token && user) {
      router.replace(getPostLoginPath(user.role));
    }
  }, [isLoading, token, user, router]);

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const role = await login(userId, password);
      router.push(getPostLoginPath(role));
    } catch (err: any) {
      setError(
        err.message || "Giriş başarısız. Lütfen bilgilerinizi kontrol edin.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // Don't render form content until auth state is resolved
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div
          className="w-8 h-8 rounded-full border-2 border-slate-200 border-t-indigo-600 animate-spin"
          aria-label="Yükleniyor"
          role="status"
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* ── Left panel: brand (desktop only) ── */}
      <aside className="hidden lg:flex lg:w-[44%] xl:w-[40%] bg-slate-900 flex-col justify-between p-12 shrink-0">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-2.5 mb-20">
            <ToothIcon className="w-7 h-7 text-indigo-400" />
            <span className="text-white font-semibold text-lg tracking-tight">
              DentAI
            </span>
          </div>

          {/* Brand copy */}
          <div className="space-y-5">
            <h2 className="text-[2rem] font-bold text-white leading-tight">
              Klinik Simülasyon
              <br />
              Eğitim Platformu
            </h2>
            <p className="text-slate-400 text-[0.9375rem] leading-relaxed max-w-xs">
              Yapay zeka destekli hasta simülasyonları ile klinik karar verme
              becerilerinizi geliştirin.
            </p>
          </div>

          {/* Feature list */}
          <ul className="mt-12 space-y-3">
            {[
              "Gerçekçi hasta diyalogları",
              "Anlık performans geri bildirimi",
              "Vaka bazlı ilerleme takibi",
            ].map((item) => (
              <li key={item} className="flex items-center gap-2.5 text-slate-400 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-slate-600 text-xs">
          Diş Hekimliği Eğitimi için Tasarlandı
        </p>
      </aside>

      {/* ── Right panel: login form ── */}
      <main className="flex-1 flex flex-col items-center justify-center bg-white px-6 py-12 sm:px-12">
        {/* Mobile-only logo */}
        <div className="lg:hidden flex items-center gap-2 mb-10">
          <ToothIcon className="w-6 h-6 text-indigo-600" />
          <span className="font-semibold text-slate-900 text-lg tracking-tight">
            DentAI
          </span>
        </div>

        <div className="w-full max-w-sm">
          {/* Heading */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-slate-900 mb-1.5">
              Giriş Yap
            </h1>
            <p className="text-slate-500 text-sm">
              Hesabınıza erişmek için bilgilerinizi girin.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {/* Error alert */}
            {error && (
              <div
                role="alert"
                className="flex items-start gap-2.5 bg-red-50 border border-red-200 text-red-700 px-3.5 py-3 rounded-lg text-sm"
              >
                <ErrorIcon className="w-4 h-4 mt-0.5 shrink-0" />
                {error}
              </div>
            )}

            {/* User ID */}
            <div className="space-y-1.5">
              <label
                htmlFor="user_id"
                className="block text-sm font-medium text-slate-700"
              >
                Öğrenci / Kullanıcı Numarası
              </label>
              <input
                id="user_id"
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="Örn: 220601011"
                required
                autoComplete="username"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-slate-700"
              >
                Şifre
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="current-password"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              />
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-semibold py-2.5 px-4 rounded-lg text-sm shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <svg
                    className="animate-spin h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    aria-hidden="true"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Giriş yapılıyor…
                </span>
              ) : (
                "Giriş Yap"
              )}
            </button>
          </form>

          {/* Register link */}
          <p className="mt-6 text-center text-sm text-slate-500">
            Hesabınız yok mu?{" "}
            <Link
              href="/register"
              className="text-indigo-600 font-medium hover:text-indigo-700 transition-colors"
            >
              Kayıt Ol
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}

// ── Inline SVG icons ──────────────────────────────────────────────────────────

function ToothIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 2c-2.8 0-5 2-5 4.5 0 1.2.4 2.3 1 3.1L7.5 20c0 1.1.7 2 1.5 2 .7 0 1.2-.5 1.5-1.5L11 18h2l.5 2.5c.3 1 .8 1.5 1.5 1.5.8 0 1.5-.9 1.5-2l-.5-10.4c.6-.8 1-1.9 1-3.1C17 4 14.8 2 12 2z" />
    </svg>
  );
}

function ErrorIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-9v4a1 1 0 11-2 0V9a1 1 0 112 0zm0-4a1 1 0 11-2 0 1 1 0 012 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}
