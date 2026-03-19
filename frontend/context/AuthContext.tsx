'use client';

/**
 * Authentication Context
 * ======================
 * Global state management for user authentication.
 * Provides login, logout, and user state to all components.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api';

interface User {
    student_id: string;
    name: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    login: (student_id: string, password: string) => Promise<void>;
    register: (student_id: string, name: string, password: string, email?: string) => Promise<void>;
    logout: () => void;
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
        const storedStudentId = localStorage.getItem('student_id');
        const storedName = localStorage.getItem('name');

        if (storedToken && storedStudentId && storedName) {
            setToken(storedToken);
            setUser({ student_id: storedStudentId, name: storedName });
        }

        setIsLoading(false);
    }, []);

    /**
     * Login function
     */
    const login = async (student_id: string, password: string) => {
        try {
            const response = await authAPI.login(student_id, password);

            // Save to state
            setToken(response.access_token);
            setUser({
                student_id: response.student_id,
                name: response.name,
            });

            // Save to localStorage
            localStorage.setItem('access_token', response.access_token);
            localStorage.setItem('student_id', response.student_id);
            localStorage.setItem('name', response.name);
        } catch (error: any) {
            console.error('Login error:', error);
            throw new Error(error.response?.data?.detail || 'Giriş başarısız');
        }
    };

    /**
     * Register function
     */
    const register = async (student_id: string, name: string, password: string, email?: string) => {
        try {
            const response = await authAPI.register({ student_id, name, password, email });

            // Save to state
            setToken(response.access_token);
            setUser({
                student_id: response.student_id,
                name: response.name,
            });

            // Save to localStorage
            localStorage.setItem('access_token', response.access_token);
            localStorage.setItem('student_id', response.student_id);
            localStorage.setItem('name', response.name);
        } catch (error: any) {
            console.error('Register error:', error);
            throw new Error(error.response?.data?.detail || 'Kayıt başarısız');
        }
    };

    /**
     * Logout function
     */
    const logout = () => {
        setToken(null);
        setUser(null);

        localStorage.removeItem('access_token');
        localStorage.removeItem('student_id');
        localStorage.removeItem('name');

        // Redirect to home using Next.js router (SPA navigation)
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
