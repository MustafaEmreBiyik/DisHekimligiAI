"use client";

import { useEffect, useState } from "react";
import { Bell, CheckCircle, Clock } from "lucide-react";
import { notificationAPI, NotificationItem } from "@/lib/api";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    notificationAPI
      .getAll()
      .then(setNotifications)
      .finally(() => setLoading(false));
  }, []);

  const handleMarkRead = async (id: number) => {
    await notificationAPI.markAsRead(id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
  };

  const handleMarkAllRead = async () => {
    await notificationAPI.markAllAsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Bell size={24} className="text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-800">Bildirimler</h1>
          {unreadCount > 0 && (
            <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-0.5 rounded-full">
              {unreadCount} okunmamış
            </span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="text-sm text-blue-600 hover:underline"
          >
            Tümünü okundu işaretle
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Bell size={48} className="mx-auto mb-3 text-gray-300" />
          <p>Henüz bildiriminiz yok.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`border rounded-lg p-4 transition ${
                n.is_read
                  ? "bg-white border-gray-200"
                  : "bg-blue-50 border-blue-200"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  {n.type === "score_published" && (
                    <>
                      <p className="text-sm font-medium text-gray-800">
                        Puanınız yayınlandı
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        {(n.payload.question_text as string) || "Soru"} —{" "}
                        <span className="font-semibold">
                          {n.payload.score as number}/{n.payload.max_score as number}
                        </span>
                      </p>
                      {n.payload.graded_by && (
                        <p className="text-xs text-gray-500 mt-0.5">
                          Puanlayan: {n.payload.graded_by as string}
                        </p>
                      )}
                    </>
                  )}
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                    <Clock size={12} />
                    {new Date(n.created_at).toLocaleString("tr-TR")}
                  </div>
                </div>
                {!n.is_read && (
                  <button
                    onClick={() => handleMarkRead(n.id)}
                    className="text-blue-600 hover:text-blue-800 p-1"
                    title="Okundu işaretle"
                  >
                    <CheckCircle size={18} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
