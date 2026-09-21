import React, { useState, useEffect, useCallback } from 'react';
import {
  Tag, Plus, Search, ChevronDown, Calendar, Loader2,
  AlertCircle, ArrowLeft, CheckCircle, XCircle, Info
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';

const VAT_RATES = ['0', '1', '10', '20'];

function today() {
  return new Date().toISOString().slice(0, 10);
}

function fmtDate(d) {
  if (!d) return '—';
  const [y, m, day] = d.split('-');
  return `${day}.${m}.${y}`;
}

function fmtCurrency(v) {
  return parseFloat(v || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + ' ₺';
}

// ── Price Form Modal ──────────────────────────────────────────────────────────

function PriceFormModal({ open, onClose, onSaved, customerId, locations, mealTypes }) {
  const { api } = useAuth();
  const [form, setForm] = useState({
    customer_id: customerId,
    location_id: '',
    meal_type_id: '',
    effective_from: today(),
    unit_price: '',
    vat_rate: '10',
    price_includes_vat: false,
    reason: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm({
        customer_id: customerId,
        location_id: '',
        meal_type_id: '',
        effective_from: today(),
        unit_price: '',
        vat_rate: '10',
        price_includes_vat: false,
        reason: '',
      });
    }
  }, [open, customerId]);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.meal_type_id) { toast.error('Yemek tipi seçin'); return; }
    if (!form.unit_price || parseFloat(form.unit_price) <= 0) { toast.error('Geçerli bir fiyat girin'); return; }
    setSaving(true);
    try {
      await api.post('/api/prices/', {
        ...form,
        customer_id: parseInt(customerId),
        location_id: form.location_id ? parseInt(form.location_id) : null,
        meal_type_id: parseInt(form.meal_type_id),
        unit_price: parseFloat(form.unit_price),
        vat_rate: parseFloat(form.vat_rate),
        price_includes_vat: form.price_includes_vat,
      });
      toast.success('Fiyat tanımı oluşturuldu');
      onSaved();
      onClose();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Hata oluştu');
    } finally {
      setSaving(false);
    }
  };

  const activeLocations = locations.filter(l => l.status === 'active');

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md" data-testid="price-form-modal">
        <DialogHeader>
          <DialogTitle>Yeni Fiyat Tanımı</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <Label>Lokasyon (boş = müşteri geneli)</Label>
            <Select value={form.location_id || 'all'} onValueChange={v => setForm(p => ({ ...p, location_id: v === 'all' ? '' : v }))}>
              <SelectTrigger data-testid="price-location-select"><SelectValue placeholder="Tüm lokasyonlar için geçerli" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm lokasyonlar için geçerli</SelectItem>
                {activeLocations.map(l => <SelectItem key={l.id} value={String(l.id)}>{l.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Yemek Tipi <span className="text-red-500">*</span></Label>
            <Select value={form.meal_type_id} onValueChange={v => setForm(p => ({ ...p, meal_type_id: v }))}>
              <SelectTrigger data-testid="price-meal-type-select"><SelectValue placeholder="Seçin..." /></SelectTrigger>
              <SelectContent>
                {mealTypes.map(mt => <SelectItem key={mt.id} value={String(mt.id)}>{mt.name_tr}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Geçerlilik Başlangıcı <span className="text-red-500">*</span></Label>
            <input
              type="date"
              value={form.effective_from}
              onChange={e => setForm(p => ({ ...p, effective_from: e.target.value }))}
              className="w-full h-10 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              data-testid="price-effective-from"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Birim Fiyat (₺) <span className="text-red-500">*</span></Label>
              <Input
                type="number"
                step="0.0001"
                min="0.01"
                value={form.unit_price}
                onChange={e => setForm(p => ({ ...p, unit_price: e.target.value }))}
                placeholder="0.00"
                data-testid="price-unit-price"
              />
            </div>
            <div>
              <Label>KDV Oranı (%)</Label>
              <Select value={form.vat_rate} onValueChange={v => setForm(p => ({ ...p, vat_rate: v }))}>
                <SelectTrigger data-testid="price-vat-rate"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {VAT_RATES.map(r => <SelectItem key={r} value={r}>%{r}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
            <input
              type="checkbox"
              id="price-includes-vat"
              checked={form.price_includes_vat}
              onChange={e => setForm(p => ({ ...p, price_includes_vat: e.target.checked }))}
              className="w-4 h-4 accent-primary"
              data-testid="price-includes-vat"
            />
            <div>
              <Label htmlFor="price-includes-vat" className="cursor-pointer">KDV Dahil Fiyat</Label>
              <p className="text-xs text-muted-foreground">
                {form.price_includes_vat ? 'Girilen fiyata KDV dahildir (brüt fiyat)' : 'Girilen fiyata KDV dahil değildir (net fiyat)'}
              </p>
            </div>
          </div>
          <div>
            <Label>Değişiklik Nedeni</Label>
            <Input value={form.reason} onChange={e => setForm(p => ({ ...p, reason: e.target.value }))} placeholder="İsteğe bağlı..." />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Vazgeç</Button>
            <Button type="submit" disabled={saving} data-testid="price-save-btn">
              {saving && <Loader2 size={14} className="animate-spin mr-1" />}
              Oluştur
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Customer Prices Panel ─────────────────────────────────────────────────────

function CustomerPrices({ customer, locations, onBack }) {
  const { api } = useAuth();
  const [mealTypes, setMealTypes] = useState([]);
  const [prices, setPrices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [activeOnly, setActiveOnly] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [mtr, pr] = await Promise.all([
        api.get('/api/prices/meal-types'),
        api.get(`/api/prices/customer/${customer.id}${activeOnly ? '?active_only=true' : ''}`),
      ]);
      setMealTypes(mtr.data);
      setPrices(pr.data);
    } catch {
      toast.error('Fiyatlar yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, [api, customer.id, activeOnly]);

  useEffect(() => { load(); }, [load]);

  const handleDeactivate = async (priceId) => {
    if (!window.confirm('Bu fiyat tanımını devre dışı bırakmak istediğinize emin misiniz?')) return;
    try {
      await api.delete(`/api/prices/${priceId}`);
      toast.success('Fiyat devre dışı bırakıldı');
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Hata');
    }
  };

  const locationName = (locationId) => {
    if (!locationId) return 'Tüm Lokasyonlar';
    const loc = locations.find(l => l.id === locationId);
    return loc?.name || `Lokasyon #${locationId}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1 text-muted-foreground hover:text-foreground text-sm transition-colors">
          <ArrowLeft size={16} /> Müşteri Listesi
        </button>
        <Button onClick={() => setShowForm(true)} size="sm" className="gap-1" data-testid="add-price-btn">
          <Plus size={14} /> Yeni Fiyat
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <Tag size={18} className="text-primary" />
        <div>
          <h2 className="font-semibold">{customer.legal_name}</h2>
          <p className="text-sm text-muted-foreground">Fiyat Yönetimi</p>
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <input type="checkbox" id="active-only" checked={activeOnly} onChange={e => setActiveOnly(e.target.checked)} className="w-4 h-4 accent-primary" />
        <Label htmlFor="active-only" className="cursor-pointer text-sm">Sadece aktif fiyatları göster</Label>
      </div>

      <div className="bg-card border rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 flex justify-center"><Loader2 size={20} className="animate-spin text-muted-foreground" /></div>
        ) : prices.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground">
            <Tag size={36} className="mx-auto mb-3 opacity-30" />
            <p className="font-medium">Fiyat tanımı bulunmuyor</p>
            <p className="text-sm mt-1">Bu müşteri için yemek fiyatı oluşturun.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Yemek Tipi</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden md:table-cell">Lokasyon</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Geçerlilik</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Fiyat</th>
                <th className="text-center px-4 py-3 font-medium text-muted-foreground">KDV</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {prices.map(p => (
                <tr key={p.id} className={`hover:bg-muted/20 ${!p.is_active ? 'opacity-50' : ''}`} data-testid={`price-row-${p.id}`}>
                  <td className="px-4 py-3 font-medium">{p.meal_type_name}</td>
                  <td className="px-4 py-3 hidden md:table-cell text-muted-foreground">{locationName(p.location_id)}</td>
                  <td className="px-4 py-3 text-sm">
                    <span>{fmtDate(p.effective_from)}</span>
                    <span className="text-muted-foreground"> → </span>
                    <span>{p.effective_to ? fmtDate(p.effective_to) : <span className="text-emerald-600">Açık</span>}</span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {fmtCurrency(p.unit_price)}
                    {p.price_includes_vat && <span className="text-xs text-muted-foreground ml-1">(dahil)</span>}
                  </td>
                  <td className="px-4 py-3 text-center text-muted-foreground">%{p.vat_rate}</td>
                  <td className="px-4 py-3 text-right">
                    {p.is_active && (
                      <button
                        onClick={() => handleDeactivate(p.id)}
                        className="text-red-400 hover:text-red-600 transition-colors"
                        title="Devre dışı bırak"
                        data-testid={`deactivate-price-${p.id}`}
                      >
                        <XCircle size={15} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <PriceFormModal
        open={showForm}
        onClose={() => setShowForm(false)}
        onSaved={load}
        customerId={customer.id}
        locations={locations}
        mealTypes={mealTypes}
      />
    </div>
  );
}

// ── Main MealPrices Page ──────────────────────────────────────────────────────

export default function MealPrices() {
  const { api } = useAuth();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [customerLocations, setCustomerLocations] = useState([]);

  useEffect(() => {
    api.get('/api/customers/?page_size=100&status=active')
      .then(r => setCustomers(r.data.items))
      .catch(() => toast.error('Müşteriler yüklenemedi'))
      .finally(() => setLoading(false));
  }, [api]);

  const handleSelectCustomer = async (c) => {
    try {
      const { data } = await api.get(`/api/customers/${c.public_id}/locations`);
      setCustomerLocations(data);
    } catch {
      setCustomerLocations([]);
    }
    setSelectedCustomer(c);
  };

  const filtered = customers.filter(c =>
    c.legal_name.toLowerCase().includes(search.toLowerCase()) ||
    (c.display_name || '').toLowerCase().includes(search.toLowerCase()) ||
    (c.code || '').toLowerCase().includes(search.toLowerCase())
  );

  if (selectedCustomer) {
    return (
      <div className="max-w-5xl mx-auto">
        <CustomerPrices
          customer={selectedCustomer}
          locations={customerLocations}
          onBack={() => setSelectedCustomer(null)}
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Tag size={20} className="text-primary" />
        </div>
        <div>
          <h1 className="page-title">Yemek Fiyatları</h1>
          <p className="text-muted-foreground text-sm">Müşteri seçerek fiyat tanımı yapın</p>
        </div>
      </div>

      <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-sm">
        <Info size={16} className="flex-shrink-0" />
        Fiyat tanımlamak için aşağıdan bir müşteri seçin. Her müşteri için farklı lokasyon ve tarih bazlı fiyat tanımlayabilirsiniz.
      </div>

      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input className="pl-8" placeholder="Müşteri ara..." value={search} onChange={e => setSearch(e.target.value)} data-testid="price-customer-search" />
      </div>

      <div className="bg-card border rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 flex justify-center"><Loader2 size={20} className="animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground">
            <Tag size={36} className="mx-auto mb-2 opacity-30" />
            <p>Müşteri bulunamadı</p>
          </div>
        ) : (
          <div className="divide-y">
            {filtered.map(c => (
              <button
                key={c.id}
                onClick={() => handleSelectCustomer(c)}
                className="w-full text-left flex items-center gap-3 px-5 py-3.5 hover:bg-muted/30 transition-colors"
                data-testid={`price-customer-row-${c.id}`}
              >
                <div className="flex-1">
                  <div className="font-medium text-sm">{c.legal_name}</div>
                  {c.code && <div className="text-xs text-muted-foreground font-mono">{c.code}</div>}
                </div>
                <div className="flex items-center gap-2">
                  {c.status !== 'active' && <Badge className="bg-red-50 text-red-600 border-red-200 border text-xs">Pasif</Badge>}
                  <ChevronDown size={16} className="text-muted-foreground -rotate-90" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
