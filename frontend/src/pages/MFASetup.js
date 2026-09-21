import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Check, Copy } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';

export default function MFASetup() {
  const { api } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        const { data } = await api.post('/api/auth/mfa/setup');
        setSetupData(data);
      } catch (e) {
        toast.error('MFA setup başlatılamadı');
        navigate('/security');
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleVerify = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/api/auth/mfa/enable', { code: code.trim() });
      setStep(3);
      toast.success(t('auth.mfaEnabled'));
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Geçersiz kod');
    } finally {
      setLoading(false);
    }
  };

  const copyAllCodes = () => {
    navigator.clipboard.writeText(setupData?.recovery_codes?.join('\n') || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading && !setupData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <ShieldCheck size={20} className="text-primary" />
        </div>
        <h1 className="page-title">{t('auth.mfaSetupTitle')}</h1>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-2 mb-8">
        {[1, 2, 3].map(s => (
          <React.Fragment key={s}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors
              ${step >= s ? 'bg-primary text-white' : 'bg-muted text-muted-foreground'}`}>
              {step > s ? <Check size={14} /> : s}
            </div>
            {s < 3 && <div className={`flex-1 h-0.5 ${step > s ? 'bg-primary' : 'bg-muted'}`} />}
          </React.Fragment>
        ))}
      </div>

      {step === 1 && setupData && (
        <div className="space-y-6 animate-fadeInUp">
          <p className="text-sm text-muted-foreground">{t('auth.scanQRInstruction')}</p>
          <div className="flex justify-center">
            <img src={setupData.qr_image} alt="QR Code" className="w-48 h-48 border rounded-xl p-2" />
          </div>
          <div className="rounded-lg bg-muted p-3">
            <p className="text-xs text-muted-foreground mb-1">Manuel giriş kodu:</p>
            <p className="font-mono text-sm break-all">{setupData.secret}</p>
          </div>
          <Button className="w-full" onClick={() => setStep(2)} data-testid="mfa-setup-next-btn">
            Devam Et →
          </Button>
        </div>
      )}

      {step === 2 && (
        <form onSubmit={handleVerify} className="space-y-4 animate-fadeInUp">
          <p className="text-sm text-muted-foreground">
            Authenticator uygulamanızdaki 6 haneli kodu girerek kurulumu doğrulayın.
          </p>
          <div className="space-y-1.5">
            <Label>{t('auth.mfaCode')}</Label>
            <Input
              type="text"
              placeholder="000000"
              value={code}
              onChange={e => setCode(e.target.value)}
              maxLength={6}
              className="text-center text-2xl tracking-widest font-mono"
              autoFocus
              required
              data-testid="mfa-setup-code-input"
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading} data-testid="mfa-setup-verify-btn">
            {loading ? 'Doğrulanıyor...' : t('auth.verifyCode')}
          </Button>
        </form>
      )}

      {step === 3 && setupData && (
        <div className="space-y-4 animate-fadeInUp">
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
            <p className="text-sm font-medium text-amber-800 mb-1">{t('auth.recoveryCodes')}</p>
            <p className="text-xs text-amber-700">{t('auth.recoveryCodesWarning')}</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {setupData.recovery_codes?.map((c, i) => (
              <code key={i} className="bg-muted rounded-md px-3 py-2 text-sm font-mono text-center">{c}</code>
            ))}
          </div>
          <Button variant="outline" className="w-full gap-2" onClick={copyAllCodes}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? 'Kopyalandı!' : 'Tümünü Kopyala'}
          </Button>
          <Button className="w-full" onClick={() => navigate('/security')} data-testid="mfa-setup-finish-btn">
            Tamamla
          </Button>
        </div>
      )}
    </div>
  );
}
