import { createContext, useContext, useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // عند تحميل التطبيق، نتحقق هل فيه توكن محفوظ مسبقاً
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');

    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.clear();
      }
    }
    setLoading(false);
  }, []);

  // ── تسجيل الدخول ──
  const login = async (username, password) => {
    const response = await axiosClient.post('/login/', { username, password });
    const { access, refresh, user: userData } = response.data;

    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    localStorage.setItem('user', JSON.stringify(userData));

    setUser(userData);
    return userData;
  };

  // ── تسجيل الخروج ──
  const logout = () => {
    localStorage.clear();
    setUser(null);
  };

  // ── هل المستخدم مسجل دخول؟ ──
  const isAuthenticated = !!user;

  // ── هل المستخدم له دور معين؟ ──
  const hasRole = (role) => user?.role === role;

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated,
    hasRole,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook مخصص لاستخدام السياق بسهولة
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
