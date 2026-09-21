import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, FileText, Layers, ShieldCheck, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';

function StatCard({ icon: Icon, label, value, color, delay }) {
  return (
    <div className={`stat-card animate-fadeInUp ${delay}`}>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={18} className="text-white" />
        </div>
      </div>
      <p className="text-2xl font-bold font-mono">{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const { user, activeTenant, api } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [health, setHealth] = useState(null);
  const [recentAudit, setRecentAudit] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { data: h } = await api.get('/api/health');
        setHealth(h);
      } catch {}
      if (activeTenant) {
        try {
          const { data } = await api.get('/api/audit/?page_size=5');
          setRecentAudit(data.items || []);
        } catch {}
      }
    };
    fetchData();
  }, [activeTenant]);

  const severityColor = (s) => ({
    critical: 'bg-destructive/10 text-destructive border-destructive/20',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    info: 'bg-blue-50 text-blue-700 border-blue-200',
  }[s] || 'bg-muted text-muted-foreground');

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">{t('dashboard.title')}</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {t('dashboard.welcome')}, <span className="font-medium text-foreground">{user?.first_name || user?.email?.split('@')[0]}</span>
            {activeTenant && <> — <span className="text-primary font-medium">{activeTenant.name}</span></>}
          </p>
        </div>
        {user?.is_super_admin && (
          <Badge className="gap-1.5 bg-primary/10 text-primary border-primary/20 px-3 py-1.5">
            Super Admin
          </Badge>
        )}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users} label={t('users.title')} value="—" color="bg-primary" delay="delay-1" />
        <StatCard icon={FileText} label={t('documents.title')} value="—" color="bg-amber-500" delay="delay-2" />
        <StatCard icon={Layers} label={t('modules.title')} value="—" color="bg-violet-500" delay="delay-3" />
        <StatCard icon={ShieldCheck} label="MFA" value={user?.mfa_enabled ? 'Aktif' : 'Pasif'} color={user?.mfa_enabled ? 'bg-emerald-500' : 'bg-slate-500'} delay="delay-4" />
      </div>

      {/* Phase 1 info + system status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border rounded-xl p-5 animate-fadeInUp delay-2">
          <div className="flex items-start gap-3 mb-4">
            <AlertCircle size={20} className="text-primary mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-sm mb-1">Phase 1 — Core Architecture</h3>
              <p className="text-xs text-muted-foreground">{t('dashboard.placeholderMsg')}</p>
            </div>
          </div>
          <div className="space-y-2 text-xs text-muted-foreground">
            {['MySQL + Alembic migrasyonlar', 'Multi-tenant backend izolasyonu', 'JWT + Argon2id + TOTP MFA', 'Rol & yetki sistemi', 'Audit log', 'Belge merkezi & SHA-256'].map(f => (
              <div key={f} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> {f}
              </div>
            ))}
          </div>
          {!user?.mfa_enabled && (
            <Button size="sm" variant="outline" className="mt-4 w-full gap-2" onClick={() => navigate('/mfa-setup')}>
              <ShieldCheck size={14} /> MFA Kur <ArrowRight size={12} />
            </Button>
          )}
        </div>

        <div className="bg-card border rounded-xl p-5 animate-fadeInUp delay-3">
          <h3 className="font-semibold text-sm mb-4">{t('dashboard.systemStatus')}</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">API</span>
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">Online</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Veritabanı</span>
              <Badge variant="outline" className={health?.database === 'ok' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-destructive/10 text-destructive'}>
                {health?.database === 'ok' ? 'Bağlı' : 'Hata'}
              </Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Depolama</span>
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">Yerel</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Recent audit log */}
      {recentAudit.length > 0 && (
        <div className="bg-card border rounded-xl overflow-hidden animate-fadeInUp delay-4">
          <div className="flex items-center justify-between px-5 py-3 border-b">
            <h3 className="font-semibold text-sm">{t('dashboard.recentActivity')}</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/audit-log')} className="text-xs gap-1">
              Tümünü Gör <ArrowRight size={12} />
            </Button>
          </div>
          <div className="divide-y">
            {recentAudit.map(log => (
              <div key={log.id} className="flex items-center justify-between px-5 py-3 text-sm hover:bg-muted/30 transition-colors">
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className={`text-[10px] ${severityColor(log.severity)}`}>
                    {log.severity}
                  </Badge>
                  <span className="font-medium text-xs font-mono">{log.action_type}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{log.user_email}</span>
                  <span>{new Date(log.created_at).toLocaleTimeString('tr')}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
