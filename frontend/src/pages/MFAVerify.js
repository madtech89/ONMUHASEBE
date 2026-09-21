import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldCheck, ArrowLeft } from 'lucide-react';
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

export default function MFAVerify() {
  const { verifyMFA } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();

  const temp_token = location.state?.temp_token;
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [useRecovery, setUseRecovery] = useState(false);

  if (!temp_token) {
    navigate('/login');
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await verifyMFA(temp_token, code.trim());
      navigate('/dashboard');
      toast.success('Giriş başarılı');
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="w-full max-w-sm animate-fadeInUp">
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <ShieldCheck size={28} className="text-primary" />
          </div>
          <h1 className="text-2xl font-bold mb-1" style={{ fontFamily: 'Outfit' }}>
            {useRecovery ? t('auth.mfaRecoveryTitle') : t('auth.mfaTitle')}
          </h1>
          <p className="text-muted-foreground text-sm">
            {useRecovery ? t('auth.mfaRecoveryDescription') : t('auth.mfaDescription')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" data-testid="mfa-form">
          <div className="space-y-1.5">
            <Label htmlFor="mfa-code">
              {useRecovery ? t('auth.mfaRecoveryCode') : t('auth.mfaCode')}
            </Label>
            <Input
              id="mfa-code"
              type="text"
              placeholder={useRecovery ? 'XXXX-XXXX-XXXX' : '000000'}
              value={code}
              onChange={e => setCode(e.target.value)}
              maxLength={useRecovery ? 20 : 6}
              className="text-center text-xl tracking-widest font-mono"
              required
              autoFocus
              data-testid="mfa-otp-input"
            />
          </div>

          {error && (
            <div className="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive" data-testid="mfa-error">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full" disabled={loading} data-testid="mfa-submit-btn">
            {loading ? 'Doğrulanıyor...' : t('auth.mfaVerify')}
          </Button>
        </form>

        <div className="mt-6 flex flex-col gap-2 items-center">
          <button
            type="button"
            className="text-sm text-primary hover:underline"
            onClick={() => { setUseRecovery(r => !r); setCode(''); setError(''); }}
            data-testid="mfa-toggle-recovery"
          >
            {useRecovery ? t('auth.mfaCode') + ' kullan' : t('auth.mfaRecoveryLink')}
          </button>
          <button
            type="button"
            className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
            onClick={() => navigate('/login')}
          >
            <ArrowLeft size={14} /> Geri Dön
          </button>
        </div>
      </div>
    </div>
  );
}
