import React, { useState, useEffect } from 'react';
import { Shield, Plus, Check } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';

const MODULE_LABELS = { core: 'Çekirdek', documents: 'Belgeler', catering: 'Catering', customers: 'Cariler', finance: 'Finans', reports: 'Raporlar', hr: 'İK' };

export default function Roles() {
  const { api } = useAuth();
  const { t } = useLanguage();
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [selectedPerms, setSelectedPerms] = useState(new Set());
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [{ data: r }, { data: p }] = await Promise.all([
        api.get('/api/roles/'),
        api.get('/api/roles/permissions')
      ]);
      setRoles(r);
      setPermissions(p);
      if (r.length > 0 && !selected) selectRole(r[0]);
    } catch { toast.error('Roller yüklenemedi'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const selectRole = (role) => {
    setSelected(role);
    setSelectedPerms(new Set(role.permissions.map(p => p.code)));
  };

  const togglePerm = (code) => {
    setSelectedPerms(prev => {
      const next = new Set(prev);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });
  };

  const savePermissions = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await api.put(`/api/roles/${selected.id}/permissions`, { permission_codes: [...selectedPerms] });
      toast.success('Yetkiler kaydedildi');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Hata'); }
    finally { setSaving(false); }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/roles/', form);
      toast.success('Rol oluşturuldu');
      setShowCreate(false);
      setForm({ code: '', name: '' });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Hata'); }
  };

  // Group permissions by module
  const byModule = permissions.reduce((acc, p) => {
    (acc[p.module] = acc[p.module] || []).push(p);
    return acc;
  }, {});

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Shield size={20} className="text-primary" />
          </div>
          <h1 className="page-title">{t('roles.title')}</h1>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2" data-testid="create-role-btn">
          <Plus size={16} /> {t('roles.createRole')}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Role list */}
        <div className="bg-card border rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b text-sm font-semibold text-muted-foreground">Roller</div>
          <div className="divide-y">
            {loading ? (
              <div className="flex justify-center py-8">
                <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
            ) : roles.map(role => (
              <button
                key={role.id}
                onClick={() => selectRole(role)}
                className={`w-full text-left px-4 py-3 text-sm transition-colors hover:bg-muted/50 ${selected?.id === role.id ? 'bg-primary/5 border-l-2 border-primary' : ''}`}
                data-testid={`role-item-${role.code}`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{role.name}</span>
                  {role.is_system_role && <Badge variant="outline" className="text-[10px]">Sistem</Badge>}
                </div>
                <span className="text-xs text-muted-foreground font-mono">{role.code}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Permission matrix */}
        <div className="lg:col-span-2 bg-card border rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <span className="text-sm font-semibold text-muted-foreground">
              {selected ? `${selected.name} — Yetkiler` : 'Rol seçin'}
            </span>
            {selected && (
              <Button size="sm" onClick={savePermissions} disabled={saving} className="gap-1.5" data-testid="save-permissions-btn">
                <Check size={14} /> {saving ? 'Kaydediliyor...' : t('roles.savePermissions')}
              </Button>
            )}
          </div>
          {selected ? (
            <div className="p-4 space-y-4 overflow-y-auto max-h-[500px]">
              {Object.entries(byModule).map(([module, perms]) => (
                <div key={module}>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                    {MODULE_LABELS[module] || module}
                  </p>
                  <div className="space-y-1">
                    {perms.map(p => (
                      <label key={p.code} className="flex items-center gap-2.5 py-1.5 px-2 rounded hover:bg-muted/50 cursor-pointer"
                        data-testid={`perm-checkbox-${p.code}`}>
                        <input
                          type="checkbox"
                          checked={selectedPerms.has(p.code)}
                          onChange={() => togglePerm(p.code)}
                          className="accent-primary"
                        />
                        <span className="text-sm">{p.name}</span>
                        <code className="ml-auto text-[10px] font-mono text-muted-foreground">{p.code}</code>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground text-sm py-12">Sol taraftan bir rol seçin</p>
          )}
        </div>
      </div>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('roles.createRole')}</DialogTitle></DialogHeader>
          <form onSubmit={handleCreate} className="space-y-3">
            <div className="space-y-1">
              <Label>{t('roles.roleName')}</Label>
              <Input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} data-testid="create-role-name-input" />
            </div>
            <div className="space-y-1">
              <Label>{t('roles.roleCode')}</Label>
              <Input required value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value.toLowerCase().replace(/\s+/g, '_') }))} placeholder="ornek_rol" data-testid="create-role-code-input" />
            </div>
            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => setShowCreate(false)}>{t('common.cancel')}</Button>
              <Button type="submit" data-testid="create-role-submit-btn">{t('common.create')}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
