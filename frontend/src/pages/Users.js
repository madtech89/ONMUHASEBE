import React, { useState, useEffect } from 'react';
import { Users as UsersIcon, Plus, MoreVertical, Mail, CheckCircle, XCircle, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';

function statusBadge(status) {
  const map = { active: 'bg-emerald-50 text-emerald-700 border-emerald-200', invited: 'bg-blue-50 text-blue-700 border-blue-200', suspended: 'bg-red-50 text-red-700 border-red-200' };
  return map[status] || 'bg-muted text-muted-foreground';
}

export default function Users() {
  const { api } = useAuth();
  const { t } = useLanguage();
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ email: '', first_name: '', last_name: '', password: '', role_code: '' });
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const [{ data: u }, { data: r }] = await Promise.all([
        api.get('/api/users/'),
        api.get('/api/roles/')
      ]);
      setUsers(u);
      setRoles(r);
    } catch { toast.error('Kullanıcılar yüklenemedi'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post('/api/users/', form);
      toast.success(t('users.createSuccess'));
      setShowCreate(false);
      setForm({ email: '', first_name: '', last_name: '', password: '', role_code: '' });
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || 'Hata'); }
    finally { setCreating(false); }
  };

  const filtered = users.filter(u =>
    u.user.email.toLowerCase().includes(search.toLowerCase()) ||
    u.user.full_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <UsersIcon size={20} className="text-primary" />
          </div>
          <h1 className="page-title">{t('users.title')}</h1>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2" data-testid="create-user-btn">
          <Plus size={16} /> {t('users.newUser')}
        </Button>
      </div>

      <div className="bg-card border rounded-xl overflow-hidden">
        <div className="p-4 border-b">
          <Input
            placeholder={t('common.search') + '...'}
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="max-w-xs"
            data-testid="users-search-input"
          />
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-center text-muted-foreground py-12 text-sm">{t('users.noUsers')}</p>
        ) : (
          <table className="w-full data-table">
            <thead>
              <tr>
                <th className="text-left">{t('users.firstName')}</th>
                <th className="text-left">{t('common.email')}</th>
                <th className="text-left">{t('users.role')}</th>
                <th className="text-left">{t('common.status')}</th>
                <th className="text-left">MFA</th>
                <th className="text-left">{t('users.lastLogin')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((tu, i) => (
                <tr key={tu.user.id} data-testid={`user-row-${i}`}>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                        {(tu.user.first_name?.[0] || tu.user.email[0]).toUpperCase()}
                      </div>
                      <span className="font-medium text-sm">{tu.user.full_name || '—'}</span>
                    </div>
                  </td>
                  <td className="text-muted-foreground">{tu.user.email}</td>
                  <td>
                    <div className="flex flex-wrap gap-1">
                      {tu.roles.map(r => (
                        <Badge key={r} variant="outline" className="text-[10px]">{r}</Badge>
                      ))}
                      {tu.roles.length === 0 && <span className="text-xs text-muted-foreground">—</span>}
                    </div>
                  </td>
                  <td>
                    <Badge variant="outline" className={`text-[10px] ${statusBadge(tu.status)}`}>{tu.status}</Badge>
                  </td>
                  <td>
                    {tu.user.mfa_enabled
                      ? <CheckCircle size={15} className="text-emerald-500" />
                      : <XCircle size={15} className="text-slate-300" />}
                  </td>
                  <td className="text-xs text-muted-foreground">
                    {tu.user.last_login_at ? new Date(tu.user.last_login_at).toLocaleDateString('tr') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create User Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent data-testid="create-user-modal">
          <DialogHeader>
            <DialogTitle>{t('users.newUser')}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>{t('users.firstName')}</Label>
                <Input value={form.first_name} onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))} data-testid="create-user-firstname" />
              </div>
              <div className="space-y-1">
                <Label>{t('users.lastName')}</Label>
                <Input value={form.last_name} onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))} data-testid="create-user-lastname" />
              </div>
            </div>
            <div className="space-y-1">
              <Label>{t('common.email')}</Label>
              <Input type="email" required value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} data-testid="create-user-email" />
            </div>
            <div className="space-y-1">
              <Label>Şifre</Label>
              <Input type="password" required minLength={8} value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} data-testid="create-user-password" />
            </div>
            <div className="space-y-1">
              <Label>{t('users.role')}</Label>
              <Select value={form.role_code} onValueChange={v => setForm(f => ({ ...f, role_code: v }))}>
                <SelectTrigger data-testid="create-user-role-select">
                  <SelectValue placeholder="Rol seç..." />
                </SelectTrigger>
                <SelectContent>
                  {roles.map(r => (
                    <SelectItem key={r.id} value={r.code}>{r.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter className="pt-2">
              <Button variant="outline" type="button" onClick={() => setShowCreate(false)}>{t('common.cancel')}</Button>
              <Button type="submit" disabled={creating} data-testid="create-user-submit-btn">
                {creating ? 'Oluşturuluyor...' : t('common.create')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
