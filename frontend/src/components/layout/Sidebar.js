import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, FolderOpen, Building2, Users, Shield, Layers,
  Lock, ClipboardList, Crown, Activity, UtensilsCrossed, CreditCard,
  FileText, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';

const LOGO_TEXT = 'CateringSaaS';

function NavItem({ to, icon: Icon, label, disabled, collapsed }) {
  const location = useLocation();
  const active = location.pathname === to || location.pathname.startsWith(to + '/');

  if (disabled) {
    return (
      <div className={`sidebar-link opacity-40 cursor-not-allowed ${collapsed ? 'justify-center' : ''}`}>
        <Icon size={18} className="flex-shrink-0" />
        {!collapsed && <span className="truncate">{label}</span>}
        {!collapsed && <span className="ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded bg-white/10">Soon</span>}
      </div>
    );
  }

  return (
    <Link
      to={to}
      data-testid={`nav-${to.replace(/\//g, '-').slice(1)}`}
      className={`sidebar-link ${active ? 'active' : ''} ${collapsed ? 'justify-center' : ''}`}
    >
      <Icon size={18} className="flex-shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  );
}

function SectionHeader({ label, collapsed }) {
  if (collapsed) return <div className="my-1 border-t border-white/10" />;
  return (
    <p className="px-3 pt-4 pb-1 text-[10px] font-semibold tracking-widest uppercase text-slate-500">
      {label}
    </p>
  );
}

export default function Sidebar({ open, collapsed, onClose, onToggleCollapse }) {
  const { user } = useAuth();
  const { t } = useLanguage();

  const sidebarW = collapsed ? 'w-[72px]' : 'w-64';

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={`hidden lg:flex flex-col ${sidebarW} flex-shrink-0 transition-all duration-200`}
        style={{ background: 'var(--sidebar-bg)' }}
        data-testid="sidebar"
      >
        <SidebarContent collapsed={collapsed} user={user} t={t} />
        {/* Collapse toggle */}
        <button
          data-testid="sidebar-collapse-btn"
          onClick={onToggleCollapse}
          className="mx-auto mb-4 flex items-center justify-center w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-slate-400 hover:text-white transition-colors"
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </aside>

      {/* Mobile sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-64 flex flex-col lg:hidden transition-transform duration-200 ${open ? 'translate-x-0' : '-translate-x-full'}`}
        style={{ background: 'var(--sidebar-bg)' }}
      >
        <SidebarContent collapsed={false} user={user} t={t} />
      </aside>
    </>
  );
}

function SidebarContent({ collapsed, user, t }) {
  return (
    <div className="flex flex-col h-full overflow-y-auto py-4">
      {/* Logo */}
      <div className={`flex items-center gap-2.5 px-4 mb-4 ${collapsed ? 'justify-center' : ''}`}>
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <UtensilsCrossed size={16} className="text-white" />
        </div>
        {!collapsed && (
          <span className="text-white font-bold text-base tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {LOGO_TEXT}
          </span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 space-y-0.5">
        <SectionHeader label={t('nav.general')} collapsed={collapsed} />
        <NavItem to="/dashboard" icon={LayoutDashboard} label={t('nav.dashboard')} collapsed={collapsed} />
        <NavItem to="/documents" icon={FolderOpen} label={t('nav.documents')} collapsed={collapsed} />

        <SectionHeader label={t('nav.accounting')} collapsed={collapsed} />
        <NavItem to="#" icon={FileText} label="Fatura & İrsaliye" disabled collapsed={collapsed} />
        <NavItem to="#" icon={UtensilsCrossed} label="Siparişler & Menü" disabled collapsed={collapsed} />
        <NavItem to="#" icon={CreditCard} label="Cari Hesaplar" disabled collapsed={collapsed} />

        <SectionHeader label={t('nav.organization')} collapsed={collapsed} />
        <NavItem to="/settings/tenant" icon={Building2} label={t('nav.tenantSettings')} collapsed={collapsed} />
        <NavItem to="/users" icon={Users} label={t('nav.users')} collapsed={collapsed} />
        <NavItem to="/roles" icon={Shield} label={t('nav.roles')} collapsed={collapsed} />
        <NavItem to="/modules" icon={Layers} label={t('nav.modules')} collapsed={collapsed} />

        <SectionHeader label={t('nav.securitySection')} collapsed={collapsed} />
        <NavItem to="/security" icon={Lock} label={t('nav.security')} collapsed={collapsed} />
        <NavItem to="/audit-log" icon={ClipboardList} label={t('nav.auditLog')} collapsed={collapsed} />

        {user?.is_super_admin && (
          <>
            <SectionHeader label={t('nav.superAdminSection')} collapsed={collapsed} />
            <NavItem to="/super-admin/tenants" icon={Crown} label={t('nav.tenantList')} collapsed={collapsed} />
            <NavItem to="/super-admin/system" icon={Activity} label={t('nav.systemHealth')} collapsed={collapsed} />
          </>
        )}
      </nav>
    </div>
  );
}
