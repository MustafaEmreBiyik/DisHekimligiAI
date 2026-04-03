"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  adminAPI,
  AdminUserItem,
  AppUserRole,
  authAPI,
} from "@/lib/api";
import AdminRouteGuard from "@/components/admin/AdminRouteGuard";

const ROLE_OPTIONS: AppUserRole[] = ["student", "instructor", "admin"];

function formatDate(dateText: string | null): string {
  if (!dateText) {
    return "-";
  }

  const date = new Date(dateText);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function roleLabel(role: AppUserRole): string {
  if (role === "student") {
    return "Öğrenci";
  }
  if (role === "instructor") {
    return "Eğitmen";
  }
  return "Admin";
}

function roleClass(role: AppUserRole): string {
  if (role === "student") {
    return "bg-blue-100 text-blue-700 border-blue-200";
  }
  if (role === "instructor") {
    return "bg-amber-100 text-amber-700 border-amber-200";
  }
  return "bg-violet-100 text-violet-700 border-violet-200";
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(true);
  const [showUsersTable, setShowUsersTable] = useState(true);
  const showCreateForm = true;

  const [currentAdminUserId, setCurrentAdminUserId] = useState<string | null>(null);

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<AppUserRole>("student");
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [createSuccessMessage, setCreateSuccessMessage] = useState("");
  const [createErrorMessage, setCreateErrorMessage] = useState("");

  const [editingUser, setEditingUser] = useState<AdminUserItem | null>(null);
  const [editRoleValue, setEditRoleValue] = useState<AppUserRole>("student");
  const [editArchivedValue, setEditArchivedValue] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isUpdatingUser, setIsUpdatingUser] = useState(false);
  const [editErrorMessage, setEditErrorMessage] = useState("");

  const loadUsers = useCallback(async () => {
    setIsLoadingUsers(true);

    try {
      const response = await adminAPI.getUsers();
      setUsers(response.users);
      setShowUsersTable(true);
    } catch {
      setUsers([]);
      setShowUsersTable(false);
    } finally {
      setIsLoadingUsers(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    const loadCurrentAdmin = async () => {
      try {
        const me = await authAPI.getCurrentUser();
        setCurrentAdminUserId(me.user_id);
      } catch {
        setCurrentAdminUserId(null);
      }
    };

    loadCurrentAdmin();
  }, []);

  const canEditUser = useCallback(
    (user: AdminUserItem) => {
      if (!currentAdminUserId) {
        return false;
      }
      return user.user_id !== currentAdminUserId;
    },
    [currentAdminUserId],
  );

  const sortedUsers = useMemo(
    () => [...users].sort((a, b) => (a.created_at && b.created_at ? b.created_at.localeCompare(a.created_at) : 0)),
    [users],
  );

  const handleCreateUser = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateSuccessMessage("");
    setCreateErrorMessage("");

    if (!displayName.trim() || !email.trim() || !password.trim()) {
      return;
    }

    setIsCreatingUser(true);

    try {
      await adminAPI.createUser({
        display_name: displayName.trim(),
        email: email.trim(),
        password,
        role,
      });

      setDisplayName("");
      setEmail("");
      setPassword("");
      setRole("student");
      setCreateSuccessMessage("Yeni kullanıcı başarıyla oluşturuldu.");

      if (showUsersTable) {
        await loadUsers();
      }
    } catch {
      setCreateErrorMessage("Kullanıcı oluşturulamadı.");
    } finally {
      setIsCreatingUser(false);
    }
  };

  const openEditModal = (user: AdminUserItem) => {
    if (!canEditUser(user)) {
      return;
    }

    setEditingUser(user);
    setEditRoleValue(user.role);
    setEditArchivedValue(user.is_archived);
    setEditErrorMessage("");
    setIsEditModalOpen(true);
  };

  const closeEditModal = () => {
    setIsEditModalOpen(false);
    setEditingUser(null);
    setEditErrorMessage("");
  };

  const handleUpdateUser = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!editingUser) {
      return;
    }

    setIsUpdatingUser(true);
    setEditErrorMessage("");

    try {
      await adminAPI.updateUser(editingUser.user_id, {
        role: editRoleValue,
        is_archived: editArchivedValue,
      });

      await loadUsers();
      closeEditModal();
    } catch {
      setEditErrorMessage("Kullanıcı güncellenemedi.");
    } finally {
      setIsUpdatingUser(false);
    }
  };

  return (
    <AdminRouteGuard>
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-8">
          <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/admin/dashboard"
                className="inline-flex rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Panele Dön
              </Link>
              <h1 className="text-2xl font-bold text-slate-900">Kullanıcı Yönetimi</h1>
            </div>
          </header>

          {isLoadingUsers && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 text-slate-600">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
                <span className="text-sm font-medium">Kullanıcılar yükleniyor...</span>
              </div>
            </section>
          )}

          {!isLoadingUsers && showUsersTable && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Kullanıcı Listesi</h2>

              <div className="overflow-x-auto">
                <table className="min-w-full border-separate border-spacing-y-2">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                      <th className="px-3 py-2">Ad Soyad</th>
                      <th className="px-3 py-2">E-posta</th>
                      <th className="px-3 py-2">Rol</th>
                      <th className="px-3 py-2">Durum</th>
                      <th className="px-3 py-2">Oluşturulma</th>
                      <th className="px-3 py-2">İşlem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedUsers.map((user) => {
                      const isEditDisabled = !canEditUser(user);
                      const isSelfRow = currentAdminUserId === user.user_id;

                      return (
                        <tr key={user.user_id} className="bg-slate-50 text-sm text-slate-800">
                          <td className="px-3 py-2 font-medium">{user.display_name}</td>
                          <td className="px-3 py-2">{user.email || "-"}</td>
                          <td className="px-3 py-2">
                            <span
                              className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${roleClass(
                                user.role,
                              )}`}
                            >
                              {roleLabel(user.role)}
                            </span>
                          </td>
                          <td className="px-3 py-2">{user.is_archived ? "Arşivde" : "Aktif"}</td>
                          <td className="px-3 py-2">{formatDate(user.created_at)}</td>
                          <td className="px-3 py-2">
                            <button
                              type="button"
                              onClick={() => openEditModal(user)}
                              disabled={isEditDisabled}
                              title={isSelfRow ? "Admin kendi hesabını düzenleyemez" : "Düzenle"}
                              className="inline-flex rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              Düzenle
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {showCreateForm && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Yeni Kullanıcı</h2>

              <form className="grid grid-cols-1 gap-4 md:grid-cols-2" onSubmit={handleCreateUser}>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="display-name">
                    Ad Soyad
                  </label>
                  <input
                    id="display-name"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                    placeholder="Örn: Ayşe Yılmaz"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="email">
                    E-posta
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                    placeholder="ornek@dentai.com"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="password">
                    Şifre
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                    placeholder="En az 6 karakter"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="role">
                    Rol
                  </label>
                  <select
                    id="role"
                    value={role}
                    onChange={(event) => setRole(event.target.value as AppUserRole)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                  >
                    {ROLE_OPTIONS.map((roleItem) => (
                      <option key={roleItem} value={roleItem}>
                        {roleLabel(roleItem)}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="md:col-span-2 flex flex-wrap items-center gap-3">
                  <button
                    type="submit"
                    disabled={isCreatingUser}
                    className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isCreatingUser ? "Kaydediliyor..." : "Kaydet"}
                  </button>

                  {createSuccessMessage && (
                    <span className="text-sm font-medium text-emerald-700">{createSuccessMessage}</span>
                  )}
                  {createErrorMessage && (
                    <span className="text-sm font-medium text-rose-700">{createErrorMessage}</span>
                  )}
                </div>
              </form>
            </section>
          )}
        </div>
      </div>

      {isEditModalOpen && editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">Kullanıcı Düzenle</h3>
              <button
                type="button"
                onClick={closeEditModal}
                className="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Kapat
              </button>
            </div>

            <form className="space-y-4" onSubmit={handleUpdateUser}>
              <div>
                <p className="text-sm font-semibold text-slate-900">{editingUser.display_name}</p>
                <p className="text-xs text-slate-500">{editingUser.email || "-"}</p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="edit-role">
                  Rol
                </label>
                <select
                  id="edit-role"
                  value={editRoleValue}
                  onChange={(event) => setEditRoleValue(event.target.value as AppUserRole)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500"
                >
                  {ROLE_OPTIONS.map((roleItem) => (
                    <option key={roleItem} value={roleItem}>
                      {roleLabel(roleItem)}
                    </option>
                  ))}
                </select>
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-700" htmlFor="edit-archived">
                <input
                  id="edit-archived"
                  type="checkbox"
                  checked={editArchivedValue}
                  onChange={(event) => setEditArchivedValue(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300"
                />
                Arşivde olarak işaretle
              </label>

              {editErrorMessage && <p className="text-sm font-medium text-rose-700">{editErrorMessage}</p>}

              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={isUpdatingUser}
                  className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isUpdatingUser ? "Kaydediliyor..." : "Kaydet"}
                </button>
                <button
                  type="button"
                  onClick={closeEditModal}
                  className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Vazgeç
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AdminRouteGuard>
  );
}
