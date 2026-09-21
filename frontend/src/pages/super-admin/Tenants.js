import React, { useState, useEffect } from 'react';
import { Crown, Plus, Activity, Users, FileText, Layers, ToggleLeft, ToggleRight } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { toast } from 'sonner';

function statusStyle(status) {
  return {
    active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    suspended: 'bg-red-50 text-red-700 border-red-200',
    disabled: 'bg-muted text-muted-foreground',
  }[status] || 'bg-muted text-muted-foreground';
}

export default function SuperAdminTenants() {
  const { api } = useAuth();
  const { t } = useLanguage();

  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', short_name: '' });
  const [creating, setCreating] = useState(false);
  const [statsMap, setStatsMap] = useState({});
  const [loadingStats, setLoadingStats] = useState({});

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/super-admin/tenants');
      setTenants(data);
    } catch {
      toast.error('Kiracılar yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const loadStats = async (tenantId) => {
    if (statsMap[tenantId] || loadingStats[tenantId]) return;
    setLoadingStats(s => ({ ...s, [tenantId]: true }));
    try {
      const { data } = await api.get(`/api/super-admin/tenants/${tenantId}/stats`);
      setStatsMap(s => ({ ...s, [tenantId]: data }));
    } catch {
      // silently fail
    } finally {
      setLoadingStats(s => ({ ...s, [tenantId]: false }));
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post('/api/super-admin/tenants', form);
      toast.success('Kiracı oluşturuldu');
      setShowCreate(false);
      setForm({ name: '', short_name: '' });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Oluşturma hatası');
    } finally {
      setCreating(false);
    }
  };

  const toggleStatus = async (tenant) => {
    const newStatus = tenant.status === 'active' ? 'suspended' : 'active';
    const label = newStatus === 'suspended' ? 'askıya alınsın' : 'aktif yapılsın';
    if (!window.confirm(`"${tenant.name}" ${label} mı?`)) return;
    try {
      await api.put(`/api/super-admin/tenants/${tenant.id}/status`, { status: newStatus });
      toast.success(`Kiracı durumu güncellendi: ${newStatus}`);
      load();
    } catch {
      toast.error('Durum güncellenemedi');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
            <Crown size={20} className="text-amber-600" />
          </div>
          <div>
            <h1 className="page-title">{t('superAdmin.title')}</h1>
            <p className="text-xs text-muted-foreground mt-0.5">{tenants.length} kiracı</p>
          </div>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2" data-testid="create-tenant-btn">
          <Plus size={16} /> {t('superAdmin.createTenant')}
        </Button>
      </div>

      {/* Tenant list */}
      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="flex items-center justify-center py-16 bg-card border rounded-xl">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : tenants.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 bg-card border rounded-xl gap-3">
            <Crown size={40} className="text-muted-foreground/40" />
            <p className="text-muted-foreground text-sm">Henüz kiracı yok</p>
          </div>
        ) : (
          tenants.map((tenant, i) => {
            const stats = statsMap[tenant.id];
            return (
              <div
                key={tenant.id}
                className="bg-card border rounded-xl p-5 animate-fadeInUp"
                style={{ animationDelay: `${i * 0.04}s` }}
                data-testid={`tenant-card-${i}`}
                onMouseEnter={() => loadStats(tenant.id)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold flex-shrink-0">
                      {(tenant.short_name || tenant.name)[0].toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-sm">{tenant.name}</h3>
                        {tenant.short_name && (
                          <span className="text-xs text-muted-foreground font-mono">[{tenant.short_name}]</span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5 truncate">{tenant.public_id}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Oluşturulma: {tenant.created_at ? new Date(tenant.created_at).toLocaleDateString('tr') : '—'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    {/* Stats */}
                    {stats ? (
                      <div className="hidden sm:flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1"><Users size={11} /> {stats.user_count}</span>
                        <span className="flex items-center gap-1"><FileText size={11} /> {stats.document_count}</span>
                        <span className="flex items-center gap-1"><Layers size={11} /> {stats.active_modules}</span>
                      </div>
                    ) : loadingStats[tenant.id] ? (
                      <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    ) : null}

                    <Badge variant="outline" className={`text-[10px] ${statusStyle(tenant.status)}`} data-testid={`tenant-status-${i}`}>
                      {tenant.status === 'active' ? 'Aktif' : tenant.status === 'suspended' ? 'Askıda' : 'Devre Dışı'}
                    </Badge>

                    <Button
                      size="sm"
                      variant="outline"
                      className={`gap-1.5 text-xs ${tenant.status === 'active' ? 'text-amber-600 border-amber-200' : 'text-emerald-600 border-emerald-200'}`}
                      onClick={() => toggleStatus(tenant)}
                      data-testid={`tenant-toggle-btn-${i}`}
                    >
                      {tenant.status === 'active' ? (
                        <><ToggleRight size={13} /> Askıya Al</>
                      ) : (
                        <><ToggleLeft size={13} /> Aktif Et</>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Create Tenant Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent data-testid="create-tenant-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus size={16} /> {t('superAdmin.createTenant')}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-1.5">
              <Label>{t('superAdmin.tenantName')}</Label>
              <Input
                required
                placeholder="Örnek Yemek A.Ş."
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                data-testid="create-tenant-name-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Kısa Ad</Label>
              <Input
                placeholder="EY"
                value={form.short_name}
                onChange={e => setForm(f => ({ ...f, short_name: e.target.value.toUpperCase().slice(0, 10) }))}
                data-testid="create-tenant-short-name-input"
              />
            </div>
            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => { setShowCreate(false); setForm({ name: '', short_name: '' }); }}>Vazgeç</Button>
              <Button type="submit" disabled={creating} data-testid="create-tenant-submit-btn">
                {creating ? 'Oluşturuluyor...' : 'Oluştur'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
