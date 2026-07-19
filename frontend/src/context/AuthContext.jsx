import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, AUTH_SESSION_EXPIRED_EVENT } from '../utils/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore session on initial load or page refresh
    restoreSession();

    // Listen for global session expiration events dispatched by api.js
    const handleSessionExpired = () => {
      logout();
    };

    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, handleSessionExpired);
    return () => {
      window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, handleSessionExpired);
    };
  }, []);

  const restoreSession = async () => {
    const savedToken = localStorage.getItem('token');
    const savedRole = localStorage.getItem('role');
    const savedUsername = localStorage.getItem('username');

    if (!savedToken) {
      setLoading(false);
      return;
    }

    try {
      const profile = await api.auth.me();
      setUser({
        username: profile.username || savedUsername,
        role: profile.role || savedRole,
        ...profile
      });
      setToken(savedToken);
    } catch (err) {
      // If token verification fails (expired or invalid), clear session
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const data = await api.auth.login(username, password);
    setToken(data.access_token);
    setUser({
      username: data.username,
      role: data.role
    });
    return data;
  };

  const logout = () => {
    api.auth.logout();
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token && !!user,
    login,
    logout,
    restoreSession
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
