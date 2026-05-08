"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authAPI } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface AdminRouteGuardProps {
  children: React.ReactNode;
}

export default function AdminRouteGuard({ children }: AdminRouteGuardProps) {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  const [isCheckingRole, setIsCheckingRole] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    if (authLoading) {
      return;
    }

    if (!user) {
      router.replace("/login");
      setIsCheckingRole(false);
      return;
    }

    // Use stored role when available to avoid an extra round-trip
    if (user.role) {
      setHasAccess(user.role === "admin");
      if (user.role !== "admin") {
        router.replace("/dashboard");
      }
      setIsCheckingRole(false);
      return;
    }

    // Fallback: verify role with backend (handles stale localStorage edge cases)
    const checkRole = async () => {
      try {
        const me = await authAPI.getCurrentUser();

        if (me.role === "admin") {
          setHasAccess(true);
        } else {
          router.replace("/dashboard");
        }
      } catch {
        router.replace("/dashboard");
      } finally {
        setIsCheckingRole(false);
      }
    };

    checkRole();
  }, [authLoading, router, user]);

  if (authLoading || isCheckingRole) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-600 shadow-sm">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
          <span className="text-sm font-medium">Admin yetkisi kontrol ediliyor...</span>
        </div>
      </div>
    );
  }

  if (!hasAccess) {
    return null;
  }

  return <>{children}</>;
}
