'use client';

/**
 * Authentication Context
 * ======================
 * Global state management for user authentication.
 * Provides login, logout, and user state to all components.
 * Role is always sourced from the backend (/api/auth/me) — never from client input.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI, AppUserRole } from '@/lib/api';

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
    register: (student_id: string, name: string, password: string, email?: string) => Promise<void>;
    logout: () => void;
}

const AUTH_KEYS = ['access_token', 'user_id', 'student_id', 'name', 'display_name', 'role'] as const;

function clearAuthStorage() {
    AUTH_KEYS.forEach((key) => localStorage.removeItem(key));
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Initialize auth state from localStorage on mount
    useEffect(() => {
        const storedToken = localStorage.getItem('access_token');
        const storedUserId = localStorage.getItem('user_id');
        const storedStudentId = localStorage.getItem('student_id');
        const storedName = localStorage.getItem('name');
        const storedDisplayName = localStorage.getItem('display_name');
        const storedRole = localStorage.getItem('role') as AppUserRole | null;

        if (storedToken && storedStudentId && storedName && storedRole) {
            setToken(storedToken);
            setUser({
                user_id: storedUserId ?? '',
                student_id: storedStudentId,
                name: storedName,
                display_name: storedDisplayName ?? storedName,
                role: storedRole,
            });
        }

        setIsLoading(false);
    }, []);

    /**
     * Login function — returns the backend-assigned role for post-login routing.
     */
    const login = async (student_id: string, password: string): Promise<AppUserRole> => {
        try {
            const response = await authAPI.login(student_id, password);

            // Persist token immediately so the /me request is authenticated
            localStorage.setItem('access_token', response.access_token);
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

            localStorage.setItem('user_id', me.user_id);
            localStorage.setItem('student_id', me.student_id);
            localStorage.setItem('name', me.name);
            localStorage.setItem('display_name', me.display_name);
            localStorage.setItem('role', me.role);

            return me.role;
        } catch (error: any) {
            // Clean up any partially stored data on failure
            clearAuthStorage();
            setToken(null);
            setUser(null);
            console.error('Login error:', error);
            throw new Error(error.response?.data?.detail || 'Giriş başarısız');
        }
    };

    /**
     * Register function (student self-service only).
     */
    const register = async (student_id: string, name: string, password: string, email?: string) => {
        try {
            const response = await authAPI.register({ student_id, name, password, email });

            localStorage.setItem('access_token', response.access_token);
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

            localStorage.setItem('user_id', me.user_id);
            localStorage.setItem('student_id', me.student_id);
            localStorage.setItem('name', me.name);
            localStorage.setItem('display_name', me.display_name);
            localStorage.setItem('role', me.role);
        } catch (error: any) {
            clearAuthStorage();
            setToken(null);
            setUser(null);
            console.error('Register error:', error);
            throw new Error(error.response?.data?.detail || 'Kayıt başarısız');
        }
    };

    /**
     * Logout function — clears all auth state.
     */
    const logout = () => {
        setToken(null);
        setUser(null);
        clearAuthStorage();
        router.push('/');
    };

    return (
        <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
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
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
