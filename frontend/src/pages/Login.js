import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { UtensilsCrossed, Eye, EyeOff, Globe } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';

function getApiError(error) {
  const detail = error?.response?.data?.detail;
  if (!detail) return error?.message || 'Bir hata oluştu.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(e => e.msg || JSON.stringify(e)).join(', ');
  return String(detail);
}

export default function Login() {
  const { login } = useAuth();
  const { language, switchLanguage, t } = useLanguage();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await login(email, password);
      if (result.requires_mfa) {
        navigate('/mfa', { state: { temp_token: result.temp_token } });
      } else {
        navigate('/dashboard');
        toast.success('Başarıyla giriş yapıldı');
      }
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left panel - branding */}
      <div
        className="hidden lg:flex flex-col justify-between w-1/2 p-12"
        style={{ background: 'var(--sidebar-bg)' }}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
            <UtensilsCrossed size={20} className="text-white" />
          </div>
          <span className="text-white font-bold text-xl" style={{ fontFamily: 'Outfit' }}>CateringSaaS</span>
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white mb-4" style={{ fontFamily: 'Outfit' }}>
            Catering & Küçük İşletme<br />Ön Muhasebe Platformu
          </h1>
          <p className="text-slate-400 text-base mb-8">
            Profesyonel muhasebe, operasyon ve belge yönetimi.
            Multi-tenant SaaS mimarisi ile ölçeklenebilir yapı.
          </p>
          <ul className="space-y-3">
            {['Çok kiracılı güvenli izolasyon', 'Rol tabanlı yetki sistemi', 'Audit log & izlenebilirlik', 'Belge merkezi & OCR hazırlığı', 'MFA & kurumsal güvenlik'].map((f) => (
              <li key={f} className="flex items-center gap-2 text-slate-300 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                {f}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-slate-600 text-xs">© 2026 CateringSaaS — Phase 1</p>
      </div>

      {/* Right panel - form */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 sm:p-12">
        {/* Lang toggle top right */}
        <div className="absolute top-4 right-4">
          <Button
            variant="ghost" size="sm"
            onClick={() => switchLanguage(language === 'tr' ? 'en' : 'tr')}
            data-testid="login-lang-toggle"
            className="gap-1.5 text-xs font-semibold text-muted-foreground"
          >
            <Globe size={14} /> {language.toUpperCase()}
          </Button>
        </div>

        <div className="w-full max-w-sm animate-fadeInUp">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
              <UtensilsCrossed size={18} className="text-white" />
            </div>
            <span className="font-bold text-lg" style={{ fontFamily: 'Outfit' }}>CateringSaaS</span>
          </div>

          <h2 className="text-2xl font-bold mb-1" style={{ fontFamily: 'Outfit' }}>{t('auth.login')}</h2>
          <p className="text-muted-foreground text-sm mb-8">Hesabınıza giriş yapın</p>

          <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
            <div className="space-y-1.5">
              <Label htmlFor="email">{t('auth.email')}</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
                data-testid="login-email-input"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">{t('auth.password')}</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowPassword(s => !s)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive" data-testid="login-error">
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={loading}
              data-testid="login-submit-btn"
            >
              {loading ? t('auth.loggingIn') : t('auth.loginButton')}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
