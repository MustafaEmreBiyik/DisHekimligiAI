"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { AppUserRole } from "@/lib/api";

function getPostLoginPath(role: AppUserRole): string {
  if (role === "instructor") return "/instructor/dashboard";
  if (role === "admin") return "/admin/dashboard";
  return "/dashboard";
}

export default function Home() {
  const { isLoading, token, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (token && user) {
      router.replace(getPostLoginPath(user.role));
    } else {
      router.replace("/login");
    }
  }, [isLoading, token, user, router]);

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
