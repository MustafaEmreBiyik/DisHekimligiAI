"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  adminAPI,
  AdminHealthResponse,
  ServiceHealthStatus,
} from "@/lib/api";
import AdminRouteGuard from "@/components/admin/AdminRouteGuard";

function statusLabel(status: ServiceHealthStatus): string {
  if (status === "ok") {
    return "Çalışıyor";
  }
  if (status === "degraded") {
    return "Yavaşladı";
  }
  return "Erişilemiyor";
}

function statusClass(status: ServiceHealthStatus): string {
  if (status === "ok") {
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }
  if (status === "degraded") {
    return "bg-amber-100 text-amber-700 border-amber-200";
  }
  return "bg-rose-100 text-rose-700 border-rose-200";
}

export default function AdminDashboardPage() {
  const [health, setHealth] = useState<AdminHealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showServices, setShowServices] = useState(true);
  const [showStats, setShowStats] = useState(true);

  useEffect(() => {
    const loadHealth = async () => {
      setIsLoading(true);

      try {
        const response = await adminAPI.getHealth();
        setHealth(response);
        setShowServices(true);
        setShowStats(true);
      } catch {
        setHealth(null);
        setShowServices(false);
        setShowStats(false);
      } finally {
        setIsLoading(false);
      }
    };

    loadHealth();
  }, []);

  return (
    <AdminRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">
          <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 className="text-3xl font-bold text-slate-900">Admin Paneli</h1>
            <p className="mt-2 text-sm text-slate-600">
              Sistem durumu ve yönetim araçlarına hızlı erişim
            </p>
          </header>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-xl font-bold text-slate-900">Hızlı Erişim</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Link
                href="/admin/users"
                className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-100"
              >
                Kullanıcı Yönetimi
              </Link>
              <Link
                href="/admin/cases"
                className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-100"
              >
                Vaka Kataloğu
              </Link>
              <Link
                href="/admin/dashboard#sistem-sagligi"
                className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-100"
              >
                Sistem Sağlığı
              </Link>
            </div>
          </section>

          {isLoading && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 text-slate-600">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
                <span className="text-sm font-medium">Admin panel verileri yükleniyor...</span>
              </div>
            </section>
          )}

          {!isLoading && showServices && health && (
            <section
              id="sistem-sagligi"
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <h2 className="mb-4 text-xl font-bold text-slate-900">Servis Sağlık Kartları</h2>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {[
                  { key: "database", label: "Veritabanı" },
                  { key: "gemini_api", label: "Gemini API" },
                  { key: "medgemma_api", label: "MedGemma API" },
                ].map((service) => {
                  const value = health.services[service.key as keyof AdminHealthResponse["services"]];

                  return (
                    <article
                      key={service.key}
                      className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                    >
                      <h3 className="text-sm font-semibold text-slate-900">{service.label}</h3>
                      <span
                        className={`mt-2 inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass(
                          value,
                        )}`}
                      >
                        {statusLabel(value)}
                      </span>
                    </article>
                  );
                })}
              </div>
            </section>
          )}

          {!isLoading && showStats && health && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">İstatistik Kartları</h2>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <article className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Toplam Kullanıcı</p>
                  <p className="mt-2 text-2xl font-bold text-slate-900">{health.stats.total_users}</p>
                </article>

                <article className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Bugünkü Aktif Oturum</p>
                  <p className="mt-2 text-2xl font-bold text-slate-900">
                    {health.stats.active_sessions_today}
                  </p>
                </article>

                <article className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Bugünkü Güvenlik İhlali</p>
                  <p className="mt-2 text-2xl font-bold text-slate-900">
                    {health.stats.safety_flags_today}
                  </p>
                </article>

                <article className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Bugünkü Prompt Enjeksiyon Girişimi
                  </p>
                  <p className="mt-2 text-2xl font-bold text-slate-900">
                    {health.stats.injection_attempts_today}
                  </p>
                </article>
              </div>
            </section>
          )}
        </div>
      </div>
    </AdminRouteGuard>
  );
}
