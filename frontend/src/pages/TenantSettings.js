import React, { useState, useEffect, useRef } from 'react';
import { Building2, Save, Upload, Image, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function TenantSettings() {
  const { activeTenant, api } = useAuth();
  const { t } = useLanguage();
  const [form, setForm] = useState({
    ticari_unvan: '', kisa_ad: '', vergi_dairesi: '', vergi_no: '',
    adres: '', telefon: '', eposta: '', website: '',
    para_birimi: 'TRY', kdv_orani: '20', timezone: 'Europe/Istanbul',
    iban: '', banka_bilgileri: '', pdf_header: '', pdf_footer: '',
  });
  const [loading, setLoading] = useState(false);
  const [logoUrl, setLogoUrl] = useState(null);
  const [logoUploading, setLogoUploading] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    const load = async () => {
      if (!activeTenant) return;
      try {
        const { data } = await api.get(`/api/tenants/${activeTenant.public_id}`);
        if (data.settings) {
          setForm(f => ({ ...f, ...data.settings }));
          if (data.settings.logo_url) setLogoUrl(`${API}${data.settings.logo_url}?t=${Date.now()}`);
        }
      } catch {}
    };
    load();
  }, [activeTenant]);

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.put(`/api/tenants/${activeTenant.public_id}/settings`, form);
      toast.success(t('tenantSettings.saved'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Kayıt hatası');
    } finally {
      setLoading(false);
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setLogoUploading(true);
    try {
      await api.post(`/api/tenants/${activeTenant.public_id}/logo`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setLogoUrl(`${API}/api/tenants/${activeTenant.public_id}/logo?t=${Date.now()}`);
      toast.success('Logo yüklendi');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Logo yükleme hatası');
    } finally {
      setLogoUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const field = (key, label, type = 'text', placeholder = '') => (
    <div className="space-y-1.5">
      <Label htmlFor={key}>{label}</Label>
      <Input id={key} type={type} placeholder={placeholder} value={form[key] || ''}
        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        data-testid={`tenant-settings-${key}`} />
    </div>
  );

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Building2 size={20} className="text-primary" />
        </div>
        <h1 className="page-title">{t('tenantSettings.title')}</h1>
      </div>

      <form onSubmit={handleSave} data-testid="tenant-settings-form">
        <Tabs defaultValue="general">
          <TabsList className="mb-6" data-testid="tenant-settings-tabs">
            <TabsTrigger value="general">Genel Bilgiler</TabsTrigger>
            <TabsTrigger value="logo">Logo / Görsel</TabsTrigger>
            <TabsTrigger value="financial">Finansal</TabsTrigger>
            <TabsTrigger value="contact">İletişim</TabsTrigger>
            <TabsTrigger value="pdf">PDF Ayarları</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="space-y-4">
            {field('ticari_unvan', t('tenantSettings.companyName'), 'text', 'Ecrin Yemek Catering A.Ş.')}
            {field('kisa_ad', t('tenantSettings.shortName'), 'text', 'Ecrin Yemek')}
            {field('vergi_dairesi', t('tenantSettings.taxOffice'))}
            {field('vergi_no', t('tenantSettings.taxNumber'))}
          </TabsContent>

          <TabsContent value="logo" className="space-y-6">
            <div className="space-y-4">
              <div>
                <Label>Firma Logosu</Label>
                <p className="text-xs text-muted-foreground mt-1">JPG, PNG, GIF, WebP veya SVG. Maksimum 5 MB.</p>
              </div>
              {/* Current logo preview */}
              <div className="flex items-start gap-4">
                <div className="w-32 h-32 rounded-xl border-2 border-dashed border-muted flex items-center justify-center bg-muted/20 overflow-hidden" data-testid="logo-preview">
                  {logoUrl ? (
                    <img src={logoUrl} alt="Logo" className="max-w-full max-h-full object-contain p-2" />
                  ) : (
                    <div className="text-center text-muted-foreground p-4">
                      <Image size={28} className="mx-auto mb-1 opacity-40" />
                      <p className="text-xs">Logo yok</p>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/jpeg,image/png,image/gif,image/webp,image/svg+xml"
                    onChange={handleLogoUpload}
                    className="hidden"
                    id="logo-upload"
                    data-testid="logo-file-input"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileRef.current?.click()}
                    disabled={logoUploading}
                    className="gap-2"
                    data-testid="logo-upload-btn"
                  >
                    <Upload size={14} />
                    {logoUploading ? 'Yükleniyor...' : 'Logo Yükle'}
                  </Button>
                  {logoUrl && (
                    <p className="text-xs text-emerald-600">Logo aktif olarak kullanımda</p>
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="financial" className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>{t('tenantSettings.currency')}</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={form.para_birimi}
                  onChange={e => setForm(f => ({ ...f, para_birimi: e.target.value }))}
                  data-testid="tenant-settings-para_birimi"
                >
                  <option value="TRY">TRY — Türk Lirası</option>
                  <option value="EUR">EUR — Euro</option>
                  <option value="USD">USD — Dolar</option>
                </select>
              </div>
              {field('kdv_orani', t('tenantSettings.vatRate'), 'text', '20')}
            </div>
            {field('iban', t('tenantSettings.iban'), 'text', 'TR00 0000 0000 0000 0000 0000 00')}
            <div className="space-y-1.5">
              <Label>{t('tenantSettings.bankInfo')}</Label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.banka_bilgileri || ''}
                onChange={e => setForm(f => ({ ...f, banka_bilgileri: e.target.value }))}
                data-testid="tenant-settings-banka_bilgileri"
              />
            </div>
          </TabsContent>

          <TabsContent value="contact" className="space-y-4">
            {field('adres', t('tenantSettings.address'))}
            {field('telefon', t('tenantSettings.phone'), 'tel')}
            {field('eposta', t('tenantSettings.email'), 'email')}
            {field('website', t('tenantSettings.website'), 'url', 'https://')}
          </TabsContent>

          <TabsContent value="pdf" className="space-y-4">
            <div className="space-y-1.5">
              <Label>{t('tenantSettings.pdfHeader')}</Label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.pdf_header || ''}
                onChange={e => setForm(f => ({ ...f, pdf_header: e.target.value }))}
                data-testid="tenant-settings-pdf_header"
              />
            </div>
            <div className="space-y-1.5">
              <Label>{t('tenantSettings.pdfFooter')}</Label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.pdf_footer || ''}
                onChange={e => setForm(f => ({ ...f, pdf_footer: e.target.value }))}
                data-testid="tenant-settings-pdf_footer"
              />
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end mt-6">
          <Button type="submit" className="gap-2" disabled={loading} data-testid="tenant-settings-save-btn">
            <Save size={16} /> {loading ? 'Kaydediliyor...' : t('common.save')}
          </Button>
        </div>
      </form>
    </div>
  );
}
