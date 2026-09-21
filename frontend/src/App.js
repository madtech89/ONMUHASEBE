import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LanguageProvider } from './contexts/LanguageContext';
import { AuthProvider } from './contexts/AuthContext';
import { Toaster } from 'sonner';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/layout/Layout';

import Login from './pages/Login';
import MFAVerify from './pages/MFAVerify';
import MFASetup from './pages/MFASetup';
import Dashboard from './pages/Dashboard';
import TenantSettings from './pages/TenantSettings';
import Users from './pages/Users';
import Roles from './pages/Roles';
import Modules from './pages/Modules';
import Documents from './pages/Documents';
import Security from './pages/Security';
import AuditLog from './pages/AuditLog';
import SuperAdminTenants from './pages/super-admin/Tenants';
import SuperAdminSystem from './pages/super-admin/SystemHealth';
import './App.css';

function AppLayout({ children }) {
  return (
    <ProtectedRoute>
      <Layout>{children}</Layout>
    </ProtectedRoute>
  );
}

function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/mfa" element={<MFAVerify />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<AppLayout><Dashboard /></AppLayout>} />
            <Route path="/settings/tenant" element={<AppLayout><TenantSettings /></AppLayout>} />
            <Route path="/users" element={<AppLayout><Users /></AppLayout>} />
            <Route path="/roles" element={<AppLayout><Roles /></AppLayout>} />
            <Route path="/modules" element={<AppLayout><Modules /></AppLayout>} />
            <Route path="/documents" element={<AppLayout><Documents /></AppLayout>} />
            <Route path="/security" element={<AppLayout><Security /></AppLayout>} />
            <Route path="/audit-log" element={<AppLayout><AuditLog /></AppLayout>} />
            <Route path="/mfa-setup" element={<AppLayout><MFASetup /></AppLayout>} />
            <Route path="/super-admin/tenants" element={
              <ProtectedRoute requireSuperAdmin><Layout><SuperAdminTenants /></Layout></ProtectedRoute>
            } />
            <Route path="/super-admin/system" element={
              <ProtectedRoute requireSuperAdmin><Layout><SuperAdminSystem /></Layout></ProtectedRoute>
            } />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </LanguageProvider>
  );
}

export default App;
