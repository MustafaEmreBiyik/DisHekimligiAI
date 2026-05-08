"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authAPI } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface InstructorRouteGuardProps {
  children: React.ReactNode;
}

const ALLOWED_ROLES = new Set(["instructor", "admin"]);

export default function InstructorRouteGuard({
  children,
}: InstructorRouteGuardProps) {
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
      setHasAccess(ALLOWED_ROLES.has(user.role));
      if (!ALLOWED_ROLES.has(user.role)) {
        router.replace("/dashboard");
      }
      setIsCheckingRole(false);
      return;
    }

    // Fallback: verify role with backend (handles stale localStorage edge cases)
    const checkRoleAccess = async () => {
      try {
        const me = await authAPI.getCurrentUser();

        if (ALLOWED_ROLES.has(me.role)) {
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

    checkRoleAccess();
  }, [authLoading, router, user]);

  if (authLoading || isCheckingRole) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-600 shadow-sm">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
          <span className="text-sm font-medium">Yetki kontrol ediliyor...</span>
        </div>
      </div>
    );
  }

  if (!hasAccess) {
    return null;
  }

  return <>{children}</>;
}
