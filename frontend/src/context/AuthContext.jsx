import { useState, useEffect, useCallback, useMemo } from 'react';
import { authAPI } from '../services/api';
import { AuthContext } from './auth';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  // We are "loading" only while a stored token is being checked against the server
  const [loading, setLoading] = useState(() => !!localStorage.getItem('token'));

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  }, []);

  const login = useCallback((tokenData) => {
    localStorage.setItem('token', tokenData.access_token);
    localStorage.setItem('user', JSON.stringify({
      id: tokenData.user_id,
      username: tokenData.username,
      role: tokenData.role,
    }));
    setToken(tokenData.access_token);
    setUser({ id: tokenData.user_id, username: tokenData.username, role: tokenData.role });
  }, []);

  // Validate the stored token and load the full account (state is only set from the async callbacks)
  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    authAPI.getMe()
      .then((res) => { if (!cancelled) { setUser(res.data); setLoading(false); } })
      .catch(() => { if (!cancelled) { logout(); setLoading(false); } });
    return () => { cancelled = true; };
  }, [token, logout]);

  const value = useMemo(() => ({
    user, token, login, logout, loading,
    isAdmin: user?.role === 'admin',
    isFarmer: user?.role === 'farmer',
  }), [user, token, login, logout, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
