import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext();
const API = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({ baseURL: API, withCredentials: true });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);      // null=loading, false=unauthenticated, obj=user
  const [tenants, setTenants] = useState([]);
  const [activeTenant, setActiveTenant] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchTenants = useCallback(async (currentUser) => {
    if (!currentUser) return;
    try {
      const { data } = await api.get('/api/tenants/my');
      setTenants(data);
      // Auto-select first tenant
      if (data.length > 0) {
        const saved = localStorage.getItem('activeTenantId');
        const match = saved ? data.find(t => t.public_id === saved) : null;
        setActiveTenant(match || data[0]);
      }
    } catch (e) {
      setTenants([]);
    }
  }, []);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get('/api/auth/me');
      setUser(data);
      await fetchTenants(data);
    } catch (e) {
      setUser(false);
      setTenants([]);
      setActiveTenant(null);
    } finally {
      setLoading(false);
    }
  }, [fetchTenants]);

  useEffect(() => { checkAuth(); }, [checkAuth]);

  const login = async (email, password) => {
    const { data } = await api.post('/api/auth/login', { email, password });
    if (data.requires_mfa) return { requires_mfa: true, temp_token: data.temp_token };
    setUser(data.user);
    await fetchTenants(data.user);
    return { success: true };
  };

  const verifyMFA = async (temp_token, code) => {
    const { data } = await api.post('/api/auth/mfa/verify', { temp_token, code });
    setUser(data.user);
    await fetchTenants(data.user);
    return { success: true };
  };

  const logout = async () => {
    try { await api.post('/api/auth/logout'); } catch (e) { /* ignore */ }
    setUser(false);
    setTenants([]);
    setActiveTenant(null);
    localStorage.removeItem('activeTenantId');
  };

  const switchTenant = (tenant) => {
    setActiveTenant(tenant);
    localStorage.setItem('activeTenantId', tenant.public_id);
  };

  // Axios interceptor: add X-Tenant-ID header
  useEffect(() => {
    const id = api.interceptors.request.use((config) => {
      if (activeTenant) config.headers['X-Tenant-ID'] = activeTenant.public_id;
      return config;
    });
    return () => api.interceptors.request.eject(id);
  }, [activeTenant]);

  return (
    <AuthContext.Provider value={{
      user, loading, tenants, activeTenant,
      login, verifyMFA, logout, switchTenant, checkAuth,
      api,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
export { api };
