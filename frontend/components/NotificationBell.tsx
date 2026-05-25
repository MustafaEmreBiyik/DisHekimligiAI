"use client";

import { useEffect, useState, useCallback } from "react";
import { Bell } from "lucide-react";
import Link from "next/link";
import { notificationAPI } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function NotificationBell() {
  const [count, setCount] = useState(0);
  const { user } = useAuth();

  const fetchCount = useCallback(async () => {
    if (!user) return;
    try {
      const c = await notificationAPI.getUnreadCount();
      setCount(c);
    } catch {
      // ignore auth errors silently
    }
  }, [user]);

  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, 30000);
    return () => clearInterval(interval);
  }, [fetchCount]);

  if (!user) return null;

  return (
    <Link
      href="/student/notifications"
      className="relative p-2 rounded-lg hover:bg-gray-100 transition"
      title="Bildirimler"
    >
      <Bell size={20} className="text-gray-600" />
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
          {count > 99 ? "99+" : count}
        </span>
      )}
    </Link>
  );
}
