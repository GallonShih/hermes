import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

// Simple admin password - in production, this should be handled by backend
const ADMIN_PASSWORD = 'admin123';
const AUTH_STORAGE_KEY = 'yt_chat_analyzer_auth';

export const AuthProvider = ({ children }) => {
    const [isAdmin, setIsAdmin] = useState(() => {
        // Initialize from localStorage
        try {
            const stored = localStorage.getItem(AUTH_STORAGE_KEY);
            return stored === 'admin';
        } catch {
            return false;
        }
    });

    // Persist to localStorage when isAdmin changes
    useEffect(() => {
        try {
            localStorage.setItem(AUTH_STORAGE_KEY, isAdmin ? 'admin' : 'guest');
        } catch (err) {
            console.error('Failed to persist auth state:', err);
        }
    }, [isAdmin]);

    const login = useCallback((password) => {
        if (password === ADMIN_PASSWORD) {
            setIsAdmin(true);
            return { success: true };
        }
        return { success: false, error: '密碼錯誤' };
    }, []);

    const logout = useCallback(() => {
        setIsAdmin(false);
    }, []);

    const value = {
        isAdmin,
        role: isAdmin ? 'admin' : 'guest',
        login,
        logout,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export default AuthContext;
