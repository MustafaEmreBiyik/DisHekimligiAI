"use client";

/**
 * Authentication Context
 * ======================
 * Global state management for user authentication.
 * Provides login, logout, and user state to all components.
 * Role is always sourced from the backend (/api/auth/me) — never from client input.
 */

import React, { createContext, useContext, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { authAPI, AppUserRole, getApiErrorMessage } from "@/lib/api";

interface User {
  user_id: string;
  student_id: string;
  name: string;
  display_name: string;
  role: AppUserRole;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (student_id: string, password: string) => Promise<AppUserRole>;
  register: (
    student_id: string,
    name: string,
    password: string,
    email?: string,
  ) => Promise<void>;
  logout: () => void;
}

const AUTH_KEYS = [
  "access_token",
  "user_id",
  "student_id",
  "name",
  "display_name",
  "role",
] as const;

function clearAuthStorage() {
  AUTH_KEYS.forEach((key) => localStorage.removeItem(key));
}

function getStoredAuthSession(): { user: User | null; token: string | null } {
  if (typeof window === "undefined") {
    return { user: null, token: null };
  }

  const token = localStorage.getItem("access_token");
  const user_id = localStorage.getItem("user_id");
  const student_id = localStorage.getItem("student_id");
  const name = localStorage.getItem("name");
  const display_name = localStorage.getItem("display_name");
  const role = localStorage.getItem("role") as AppUserRole | null;

  if (!token || !student_id || !name || !role) {
    return { user: null, token: null };
  }

  return {
    token,
    user: {
      user_id: user_id ?? "",
      student_id,
      name,
      display_name: display_name ?? name,
      role,
    },
  };
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const initialSession = getStoredAuthSession();
  const [user, setUser] = useState<User | null>(initialSession.user);
  const [token, setToken] = useState<string | null>(initialSession.token);
  const isLoading = false;

  /**
   * Login function — returns the backend-assigned role for post-login routing.
   */
  const login = async (
    student_id: string,
    password: string,
  ): Promise<AppUserRole> => {
    try {
      const response = await authAPI.login(student_id, password);

      // Persist token immediately so the /me request is authenticated
      localStorage.setItem("access_token", response.access_token);
      setToken(response.access_token);

      // Fetch authoritative user data including role from backend
      const me = await authAPI.getCurrentUser();

      const userData: User = {
        user_id: me.user_id,
        student_id: me.student_id,
        name: me.name,
        display_name: me.display_name,
        role: me.role,
      };

      setUser(userData);

      localStorage.setItem("user_id", me.user_id);
      localStorage.setItem("student_id", me.student_id);
      localStorage.setItem("name", me.name);
      localStorage.setItem("display_name", me.display_name);
      localStorage.setItem("role", me.role);

      return me.role;
    } catch (error: unknown) {
      // Clean up any partially stored data on failure
      clearAuthStorage();
      setToken(null);
      setUser(null);
      console.error("Login error:", error);
      throw new Error(getApiErrorMessage(error, "Giris basarisiz"));
    }
  };

  /**
   * Register function (student self-service only).
   */
  const register = async (
    student_id: string,
    name: string,
    password: string,
    email?: string,
  ) => {
    try {
      const response = await authAPI.register({
        student_id,
        name,
        password,
        email,
      });

      localStorage.setItem("access_token", response.access_token);
      setToken(response.access_token);

      // Fetch authoritative user data including role from backend
      const me = await authAPI.getCurrentUser();

      const userData: User = {
        user_id: me.user_id,
        student_id: me.student_id,
        name: me.name,
        display_name: me.display_name,
        role: me.role,
      };

      setUser(userData);

      localStorage.setItem("user_id", me.user_id);
      localStorage.setItem("student_id", me.student_id);
      localStorage.setItem("name", me.name);
      localStorage.setItem("display_name", me.display_name);
      localStorage.setItem("role", me.role);
    } catch (error: unknown) {
      clearAuthStorage();
      setToken(null);
      setUser(null);
      console.error("Register error:", error);
      throw new Error(getApiErrorMessage(error, "Kayit basarisiz"));
    }
  };

  /**
   * Logout function — clears all auth state.
   */
  const logout = () => {
    setToken(null);
    setUser(null);
    clearAuthStorage();
    router.push("/");
  };

  return (
    <AuthContext.Provider
      value={{ user, token, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to use auth context
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
