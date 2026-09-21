import React, { useState, useEffect } from 'react';
import { Lock, ShieldCheck, ShieldOff, LogOut, Monitor, Smartphone, Eye, EyeOff, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';

function DeviceIcon({ userAgent }) {
  const ua = (userAgent || '').toLowerCase();
  if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone')) {
    return <Smartphone size={15} className="text-muted-foreground" />;
  }
  return <Monitor size={15} className="text-muted-foreground" />;
}

export default function Security() {
  const { user, api, logout, checkAuth } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [sessions, setSessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(true);

  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [showPw, setShowPw] = useState({ current: false, new: false });
  const [changingPw, setChangingPw] = useState(false);

  const [mfaCode, setMfaCode] = useState('');
  const [disablingMfa, setDisablingMfa] = useState(false);
  const [showDisableMfa, setShowDisableMfa] = useState(false);

  const loadSessions = async () => {
    setLoadingSessions(true);
    try {
      const { data } = await api.get('/api/auth/sessions');
      setSessions(data);
    } catch {
      toast.error('Oturumlar yüklenemedi');
    } finally {
      setLoadingSessions(false);
    }
  };

  useEffect(() => { loadSessions(); }, []);

  const handleLogoutAll = async () => {
    if (!window.confirm('Tüm cihazlardan çıkış yapılsın mı? Bu oturum da sonlanacak.')) return;
    try {
      await api.post('/api/auth/logout-all');
      toast.success('Tüm oturumlar sonlandırıldı');
      await logout();
      navigate('/login');
    } catch {
      toast.error('İşlem başarısız');
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (pwForm.new_password !== pwForm.confirm) {
      toast.error('Yeni şifreler eşleşmiyor');
      return;
    }
    if (pwForm.new_password.length < 8) {
      toast.error('Yeni şifre en az 8 karakter olmalı');
      return;
    }
    setChangingPw(true);
    try {
      await api.post('/api/auth/change-password', {
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
      });
      toast.success('Şifre değiştirildi. Yeniden giriş yapın.');
      await logout();
      navigate('/login');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Şifre değiştirme hatası');
    } finally {
      setChangingPw(false);
    }
  };

  const handleDisableMfa = async (e) => {
    e.preventDefault();
    setDisablingMfa(true);
    try {
      await api.post('/api/auth/mfa/disable', { code: mfaCode.trim() });
      toast.success('MFA devre dışı bırakıldı');
      setShowDisableMfa(false);
      setMfaCode('');
      await checkAuth();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Geçersiz kod');
    } finally {
      setDisablingMfa(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Lock size={20} className="text-primary" />
        </div>
        <h1 className="page-title">{t('security.title')}</h1>
      </div>

      {/* MFA Management */}
      <div className="bg-card border rounded-xl p-5 space-y-4" data-testid="mfa-section">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldCheck size={18} className={user?.mfa_enabled ? 'text-emerald-500' : 'text-muted-foreground'} />
            <div>
              <h2 className="font-semibold text-sm">{t('security.mfaManagement')}</h2>
              <p className="text-xs text-muted-foreground mt-0.5">İki faktörlü kimlik doğrulama (TOTP)</p>
            </div>
          </div>
          <Badge
            variant="outline"
            className={user?.mfa_enabled
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-muted text-muted-foreground'}
            data-testid="mfa-status-badge"
          >
            {user?.mfa_enabled ? 'Aktif' : 'Pasif'}
          </Badge>
        </div>

        {user?.mfa_enabled ? (
          !showDisableMfa ? (
            <Button
              variant="outline"
              size="sm"
              className="gap-2 text-destructive border-destructive/30 hover:bg-destructive/5"
              onClick={() => setShowDisableMfa(true)}
              data-testid="disable-mfa-btn"
            >
              <ShieldOff size={14} /> {t('security.disableMFA')}
            </Button>
          ) : (
            <form onSubmit={handleDisableMfa} className="space-y-3 border border-destructive/20 rounded-lg p-4 bg-destructive/5 animate-fadeInUp">
              <p className="text-sm font-medium text-destructive">MFA Devre Dışı Bırak</p>
              <p className="text-xs text-muted-foreground">Authenticator uygulamanızdaki mevcut kodu girin.</p>
              <div className="flex gap-2">
                <Input
                  type="text"
                  placeholder="000000"
                  value={mfaCode}
                  onChange={e => setMfaCode(e.target.value)}
                  maxLength={6}
                  className="font-mono tracking-widest text-center max-w-[140px]"
                  autoFocus
                  required
                  data-testid="disable-mfa-code-input"
                />
                <Button type="submit" variant="destructive" size="sm" disabled={disablingMfa} data-testid="confirm-disable-mfa-btn">
                  {disablingMfa ? 'İşleniyor...' : 'Devre Dışı Bırak'}
                </Button>
                <Button type="button" variant="ghost" size="sm" onClick={() => { setShowDisableMfa(false); setMfaCode(''); }}>
                  Vazgeç
                </Button>
              </div>
            </form>
          )
        ) : (
          <Button
            size="sm"
            className="gap-2"
            onClick={() => navigate('/mfa-setup')}
            data-testid="setup-mfa-btn"
          >
            <ShieldCheck size={14} /> {t('security.setupMFA')}
          </Button>
        )}
      </div>

      {/* Change Password */}
      <div className="bg-card border rounded-xl p-5" data-testid="change-password-section">
        <div className="flex items-center gap-3 mb-4">
          <Lock size={18} className="text-muted-foreground" />
          <h2 className="font-semibold text-sm">{t('auth.changePassword')}</h2>
        </div>
        <form onSubmit={handleChangePassword} className="space-y-4 max-w-sm">
          <div className="space-y-1.5">
            <Label htmlFor="current-pw">{t('auth.currentPassword')}</Label>
            <div className="relative">
              <Input
                id="current-pw"
                type={showPw.current ? 'text' : 'password'}
                value={pwForm.current_password}
                onChange={e => setPwForm(f => ({ ...f, current_password: e.target.value }))}
                required
                data-testid="current-password-input"
              />
              <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" onClick={() => setShowPw(s => ({ ...s, current: !s.current }))}>
                {showPw.current ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-pw">{t('auth.newPassword')}</Label>
            <div className="relative">
              <Input
                id="new-pw"
                type={showPw.new ? 'text' : 'password'}
                value={pwForm.new_password}
                onChange={e => setPwForm(f => ({ ...f, new_password: e.target.value }))}
                minLength={8}
                required
                data-testid="new-password-input"
              />
              <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" onClick={() => setShowPw(s => ({ ...s, new: !s.new }))}>
                {showPw.new ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm-pw">Yeni Şifre (Tekrar)</Label>
            <Input
              id="confirm-pw"
              type="password"
              value={pwForm.confirm}
              onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))}
              required
              data-testid="confirm-password-input"
            />
          </div>
          <Button type="submit" size="sm" disabled={changingPw} data-testid="change-password-submit-btn">
            {changingPw ? 'Değiştiriliyor...' : t('auth.changePassword')}
          </Button>
        </form>
      </div>

      {/* Active Sessions */}
      <div className="bg-card border rounded-xl overflow-hidden" data-testid="sessions-section">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <div className="flex items-center gap-2">
            <Monitor size={16} className="text-muted-foreground" />
            <h2 className="font-semibold text-sm">{t('security.activeSessions')}</h2>
            {sessions.length > 0 && (
              <Badge variant="outline" className="text-[10px]">{sessions.length}</Badge>
            )}
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" className="gap-1.5 text-xs" onClick={loadSessions} data-testid="refresh-sessions-btn">
              <RefreshCw size={12} /> Yenile
            </Button>
            <Button size="sm" variant="outline" className="gap-1.5 text-xs text-destructive border-destructive/30 hover:bg-destructive/5" onClick={handleLogoutAll} data-testid="logout-all-btn">
              <LogOut size={12} /> {t('security.logoutAll')}
            </Button>
          </div>
        </div>
        {loadingSessions ? (
          <div className="flex justify-center py-8">
            <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : sessions.length === 0 ? (
          <p className="text-center text-muted-foreground text-sm py-8">Aktif oturum yok</p>
        ) : (
          <div className="divide-y">
            {sessions.map((session, i) => (
              <div key={session.public_id} className="flex items-center justify-between px-5 py-3" data-testid={`session-row-${i}`}>
                <div className="flex items-center gap-3">
                  <DeviceIcon userAgent={session.user_agent} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{session.ip_address || 'Bilinmeyen IP'}</span>
                      {session.is_current && (
                        <Badge className="text-[10px] bg-primary/10 text-primary border-primary/20 px-1.5 py-0.5" data-testid="current-session-badge">
                          Bu oturum
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate max-w-xs">
                      {session.user_agent?.slice(0, 60) || '—'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Son görülme</p>
                    <p className="text-xs font-medium">
                      {session.last_used_at ? new Date(session.last_used_at).toLocaleString('tr') : '—'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
