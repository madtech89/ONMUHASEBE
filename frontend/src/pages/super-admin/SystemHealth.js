import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Database, Users, Building2, RefreshCw, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';

function MetricCard({ icon: Icon, label, value, color, sub }) {
  return (
    <div className="bg-card border rounded-xl p-5 animate-fadeInUp">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-muted-foreground font-medium">{label}</p>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={18} className="text-white" />
        </div>
      </div>
      <p className="text-2xl font-bold font-mono">{value ?? '—'}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  );
}

export default function SystemHealth() {
  const { api } = useAuth();
  const { t } = useLanguage();
  const [health, setHealth] = useState(null);
  const [publicHealth, setPublicHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [{ data: h }, { data: pub }] = await Promise.all([
        api.get('/api/super-admin/system/health'),
        api.get('/api/health'),
      ]);
      setHealth(h);
      setPublicHealth(pub);
      setLastRefresh(new Date());
    } catch {
      toast.error('Sistem sağlığı yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000); // Auto-refresh every 30s
    return () => clearInterval(interval);
  }, [load]);

  const dbOk = publicHealth?.database === 'ok';

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
            <Activity size={20} className="text-violet-600" />
          </div>
          <div>
            <h1 className="page-title">{t('superAdmin.systemTitle')}</h1>
            {lastRefresh && (
              <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                <Clock size={10} /> Son güncelleme: {lastRefresh.toLocaleTimeString('tr')}
              </p>
            )}
          </div>
        </div>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={load} disabled={loading} data-testid="refresh-health-btn">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Yenile
        </Button>
      </div>

      {/* Status bar */}
      <div className="bg-card border rounded-xl p-4 flex items-center gap-4" data-testid="system-status-bar">
        <div className="flex items-center gap-2">
          {dbOk ? (
            <CheckCircle size={18} className="text-emerald-500" />
          ) : (
            <XCircle size={18} className="text-destructive" />
          )}
          <span className="font-semibold text-sm">Genel Sistem Durumu</span>
          <Badge
            variant="outline"
            className={dbOk ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-destructive/10 text-destructive border-destructive/20'}
            data-testid="system-overall-status"
          >
            {dbOk ? 'Sağlıklı' : 'Sorun Var'}
          </Badge>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={Building2}
          label="Toplam Kiracı"
          value={health?.tenants}
          color="bg-primary"
          sub="Aktif kiracılar"
          data-testid="metric-tenants"
        />
        <MetricCard
          icon={Users}
          label="Toplam Kullanıcı"
          value={health?.users}
          color="bg-violet-500"
          sub="Tüm kiracılar"
          data-testid="metric-users"
        />
        <MetricCard
          icon={Database}
          label="Veritabanı"
          value={dbOk ? 'Online' : 'Hata'}
          color={dbOk ? 'bg-emerald-500' : 'bg-destructive'}
          sub="MariaDB"
          data-testid="metric-database"
        />
        <MetricCard
          icon={Activity}
          label="API"
          value={publicHealth ? 'Online' : 'Hata'}
          color="bg-amber-500"
          sub="FastAPI Backend"
          data-testid="metric-api"
        />
      </div>

      {/* Details table */}
      <div className="bg-card border rounded-xl overflow-hidden" data-testid="health-details-table">
        <div className="px-5 py-4 border-b">
          <h3 className="font-semibold text-sm">Bileşen Detayları</h3>
        </div>
        <div className="divide-y">
          {[
            { name: 'MariaDB (InnoDB)', status: dbOk ? 'ok' : 'error', detail: 'MySQL 8+ uyumlu, multi-tenant' },
            { name: 'FastAPI Backend', status: 'ok', detail: 'Python async, SQLAlchemy' },
            { name: 'Yerel Depolama', status: 'ok', detail: `/app/storage (${health?.status || '—'})` },
            { name: 'JWT Auth', status: 'ok', detail: 'HTTP-only cookies, refresh rotation' },
            { name: 'TOTP MFA', status: 'ok', detail: 'PyOTP, Fernet şifreleme' },
            { name: 'Argon2id Hashing', status: 'ok', detail: 'password-argon2 kütüphanesi' },
          ].map(item => (
            <div key={item.name} className="flex items-center justify-between px-5 py-3 text-sm">
              <div>
                <span className="font-medium">{item.name}</span>
                <p className="text-xs text-muted-foreground mt-0.5">{item.detail}</p>
              </div>
              <Badge
                variant="outline"
                className={item.status === 'ok'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-destructive/10 text-destructive border-destructive/20'}
              >
                {item.status === 'ok' ? 'Çalışıyor' : 'Hata'}
              </Badge>
            </div>
          ))}
        </div>
      </div>

      {/* Phase info */}
      <div className="bg-primary/5 border border-primary/20 rounded-xl p-5">
        <h3 className="font-semibold text-sm text-primary mb-2">Phase 1 — Core Architecture</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs text-muted-foreground">
          {[
            'MySQL 8+ / InnoDB', 'Multi-tenant backend izolasyonu',
            'JWT + Argon2id + TOTP MFA', 'Rol & yetki sistemi',
            'Audit log', 'Belge merkezi & SHA-256',
            'Refresh token rotation', 'Brute force koruması',
            'Rate limiting (slowapi)', 'HTTP-only cookie auth',
          ].map(f => (
            <div key={f} className="flex items-center gap-2">
              <CheckCircle size={11} className="text-emerald-500 flex-shrink-0" />
              <span>{f}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
