import React, { useState, useEffect, useCallback } from 'react';
import {
  Users, Plus, Search, ChevronRight, MapPin, Phone, Mail,
  Building2, Edit2, XCircle, CheckCircle, Loader2, X, ArrowLeft
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';

const LOCATION_TYPES = [
  { value: 'santiye', label: 'Şantiye' },
  { value: 'ofis', label: 'Ofis' },
  { value: 'isyeri', label: 'İşyeri' },
  { value: 'fabrika', label: 'Fabrika' },
  { value: 'depo', label: 'Depo' },
  { value: 'sube', label: 'Şube' },
  { value: 'diger', label: 'Diğer' },
];

const CUSTOMER_TYPES = [
  { value: 'company', label: 'Şirket' },
  { value: 'individual', label: 'Bireysel' },
  { value: 'other', label: 'Diğer' },
];

function StatusBadge({ status }) {
  return status === 'active'
    ? <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 border text-xs">Aktif</Badge>
    : <Badge className="bg-red-50 text-red-700 border-red-200 border text-xs">Pasif</Badge>;
}

// ── Customer Form Modal ──────────────────────────────────────────────────────

function CustomerFormModal({ open, onClose, onSaved, existing = null }) {
  const { api } = useAuth();
  const [form, setForm] = useState({
    legal_name: '', display_name: '', code: '', customer_type: 'company',
    tax_office: '', tax_number: '', phone: '', email: '', address: '', notes: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (existing) {
      setForm({
        legal_name: existing.legal_name || '',
        display_name: existing.display_name || '',
        code: existing.code || '',
        customer_type: existing.customer_type || 'company',
        tax_office: existing.tax_office || '',
        tax_number: existing.tax_number || '',
        phone: existing.phone || '',
        email: existing.email || '',
        address: existing.address || '',
        notes: existing.notes || '',
      });
    } else {
      setForm({ legal_name: '', display_name: '', code: '', customer_type: 'company', tax_office: '', tax_number: '', phone: '', email: '', address: '', notes: '' });
    }
  }, [existing, open]);

  const f = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.legal_name.trim()) { toast.error('Ünvan zorunludur'); return; }
    setSaving(true);
    try {
      if (existing) {
        await api.put(`/api/customers/${existing.public_id}`, form);
        toast.success('Müşteri güncellendi');
      } else {
        await api.post('/api/customers/', form);
        toast.success('Müşteri oluşturuldu');
      }
      onSaved();
      onClose();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Hata oluştu');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="customer-form-modal">
        <DialogHeader>
          <DialogTitle>{existing ? 'Müşteri Düzenle' : 'Yeni Müşteri'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label>Ünvan / Adı <span className="text-red-500">*</span></Label>
              <Input data-testid="customer-legal-name" value={form.legal_name} onChange={f('legal_name')} placeholder="Tam ticari ünvan" required />
            </div>
            <div>
              <Label>Kısa Ad</Label>
              <Input data-testid="customer-display-name" value={form.display_name} onChange={f('display_name')} placeholder="Görünen ad" />
            </div>
            <div>
              <Label>Müşteri Kodu</Label>
              <Input data-testid="customer-code" value={form.code} onChange={f('code')} placeholder="Ör: MUS001" />
            </div>
            <div>
              <Label>Müşteri Tipi</Label>
              <Select value={form.customer_type} onValueChange={v => setForm(p => ({ ...p, customer_type: v }))}>
                <SelectTrigger data-testid="customer-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CUSTOMER_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Vergi Dairesi</Label>
              <Input value={form.tax_office} onChange={f('tax_office')} placeholder="Vergi dairesi" />
            </div>
            <div>
              <Label>Vergi No / TC</Label>
              <Input value={form.tax_number} onChange={f('tax_number')} placeholder="10 haneli VKN" />
            </div>
            <div>
              <Label>Telefon</Label>
              <Input value={form.phone} onChange={f('phone')} placeholder="0212 000 00 00" />
            </div>
            <div>
              <Label>E-posta</Label>
              <Input type="email" value={form.email} onChange={f('email')} placeholder="info@firma.com" />
            </div>
            <div className="col-span-2">
              <Label>Adres</Label>
              <Input value={form.address} onChange={f('address')} placeholder="Tam adres" />
            </div>
            <div className="col-span-2">
              <Label>Notlar</Label>
              <Input value={form.notes} onChange={f('notes')} placeholder="İç notlar..." />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Vazgeç</Button>
            <Button type="submit" disabled={saving} data-testid="customer-save-btn">
              {saving ? <Loader2 size={14} className="animate-spin mr-1" /> : null}
              {existing ? 'Güncelle' : 'Oluştur'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Location Form Modal ──────────────────────────────────────────────────────

function LocationFormModal({ open, onClose, onSaved, customerPublicId, existing = null }) {
  const { api } = useAuth();
  const [form, setForm] = useState({ name: '', location_type: 'diger', address: '', contact_person: '', contact_phone: '', delivery_notes: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (existing) {
      setForm({ name: existing.name || '', location_type: existing.location_type || 'diger', address: existing.address || '', contact_person: existing.contact_person || '', contact_phone: existing.contact_phone || '', delivery_notes: existing.delivery_notes || '' });
    } else {
      setForm({ name: '', location_type: 'diger', address: '', contact_person: '', contact_phone: '', delivery_notes: '' });
    }
  }, [existing, open]);

  const f = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { toast.error('Lokasyon adı zorunludur'); return; }
    setSaving(true);
    try {
      if (existing) {
        await api.put(`/api/customers/${customerPublicId}/locations/${existing.public_id}`, form);
        toast.success('Lokasyon güncellendi');
      } else {
        await api.post(`/api/customers/${customerPublicId}/locations`, form);
        toast.success('Lokasyon eklendi');
      }
      onSaved();
      onClose();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Hata oluştu');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md" data-testid="location-form-modal">
        <DialogHeader>
          <DialogTitle>{existing ? 'Lokasyon Düzenle' : 'Yeni Lokasyon'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-3">
          <div>
            <Label>Lokasyon Adı <span className="text-red-500">*</span></Label>
            <Input data-testid="location-name" value={form.name} onChange={f('name')} placeholder="Ör: Merkez Şantiye" required />
          </div>
          <div>
            <Label>Lokasyon Tipi</Label>
            <Select value={form.location_type} onValueChange={v => setForm(p => ({ ...p, location_type: v }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {LOCATION_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Adres</Label>
            <Input value={form.address} onChange={f('address')} placeholder="Lokasyon adresi" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>İrtibat Kişisi</Label>
              <Input value={form.contact_person} onChange={f('contact_person')} placeholder="Ad Soyad" />
            </div>
            <div>
              <Label>İrtibat Telefonu</Label>
              <Input value={form.contact_phone} onChange={f('contact_phone')} placeholder="0532 000 00 00" />
            </div>
          </div>
          <div>
            <Label>Teslimat Notu</Label>
            <Input value={form.delivery_notes} onChange={f('delivery_notes')} placeholder="Teslimat bilgileri..." />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Vazgeç</Button>
            <Button type="submit" disabled={saving} data-testid="location-save-btn">
              {saving ? <Loader2 size={14} className="animate-spin mr-1" /> : null}
              {existing ? 'Güncelle' : 'Ekle'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Customer Detail Panel ────────────────────────────────────────────────────

function CustomerDetail({ customer, onBack, onRefresh }) {
  const { api } = useAuth();
  const [locations, setLocations] = useState([]);
  const [loadingLocs, setLoadingLocs] = useState(true);
  const [showLocForm, setShowLocForm] = useState(false);
  const [editingLoc, setEditingLoc] = useState(null);
  const [showEditCustomer, setShowEditCustomer] = useState(false);

  const loadLocations = useCallback(async () => {
    setLoadingLocs(true);
    try {
      const { data } = await api.get(`/api/customers/${customer.public_id}/locations`);
      setLocations(data);
    } catch {
      toast.error('Lokasyonlar yüklenemedi');
    } finally {
      setLoadingLocs(false);
    }
  }, [api, customer.public_id]);

  useEffect(() => { loadLocations(); }, [loadLocations]);

  const handleDeactivate = async () => {
    if (!window.confirm(`"${customer.legal_name}" müşterisini pasifleştirmek istediğinize emin misiniz?`)) return;
    try {
      await api.delete(`/api/customers/${customer.public_id}`);
      toast.success('Müşteri pasifleştirildi');
      onRefresh();
      onBack();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Hata');
    }
  };

  const handleLocStatusToggle = async (loc) => {
    try {
      await api.put(`/api/customers/${customer.public_id}/locations/${loc.public_id}`, {
        status: loc.status === 'active' ? 'inactive' : 'active',
      });
      toast.success('Lokasyon güncellendi');
      loadLocations();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Hata');
    }
  };

  const locTypeLabel = (t) => LOCATION_TYPES.find(l => l.value === t)?.label || t;

  return (
    <div className="space-y-6" data-testid="customer-detail">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1 text-muted-foreground hover:text-foreground text-sm transition-colors">
          <ArrowLeft size={16} /> Müşteri Listesi
        </button>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowEditCustomer(true)} data-testid="edit-customer-btn">
            <Edit2 size={14} className="mr-1" /> Düzenle
          </Button>
          {customer.status === 'active' && (
            <Button variant="outline" size="sm" className="text-red-600 border-red-200 hover:bg-red-50" onClick={handleDeactivate} data-testid="deactivate-customer-btn">
              <XCircle size={14} className="mr-1" /> Pasifleştir
            </Button>
          )}
        </div>
      </div>

      {/* Customer info card */}
      <div className="bg-card border rounded-xl p-6 space-y-4">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Building2 size={22} className="text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-semibold">{customer.legal_name}</h2>
              <StatusBadge status={customer.status} />
              {customer.code && <span className="text-xs bg-muted px-2 py-0.5 rounded font-mono">{customer.code}</span>}
            </div>
            {customer.display_name && <p className="text-muted-foreground text-sm mt-0.5">{customer.display_name}</p>}
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-2 text-sm">
          {customer.phone && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Phone size={14} /> <span>{customer.phone}</span>
            </div>
          )}
          {customer.email && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Mail size={14} /> <span>{customer.email}</span>
            </div>
          )}
          {customer.tax_number && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="font-medium">VKN:</span> <span>{customer.tax_number}</span>
              {customer.tax_office && <span>— {customer.tax_office}</span>}
            </div>
          )}
          {customer.address && (
            <div className="col-span-2 flex items-start gap-2 text-muted-foreground">
              <MapPin size={14} className="mt-0.5 flex-shrink-0" /> <span>{customer.address}</span>
            </div>
          )}
        </div>
      </div>

      {/* Locations */}
      <div className="bg-card border rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h3 className="font-semibold flex items-center gap-2">
            <MapPin size={16} className="text-primary" /> Lokasyonlar
            <span className="text-xs text-muted-foreground">({locations.length})</span>
          </h3>
          <Button size="sm" onClick={() => { setEditingLoc(null); setShowLocForm(true); }} data-testid="add-location-btn">
            <Plus size={14} className="mr-1" /> Lokasyon Ekle
          </Button>
        </div>
        {loadingLocs ? (
          <div className="p-8 flex justify-center"><Loader2 size={20} className="animate-spin text-muted-foreground" /></div>
        ) : locations.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground text-sm">
            <MapPin size={32} className="mx-auto mb-2 opacity-30" />
            Henüz lokasyon eklenmemiş
          </div>
        ) : (
          <div className="divide-y">
            {locations.map(loc => (
              <div key={loc.id} className="flex items-center gap-3 px-5 py-3 hover:bg-muted/30" data-testid={`location-row-${loc.id}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{loc.name}</span>
                    <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{locTypeLabel(loc.location_type)}</span>
                    {loc.status !== 'active' && <Badge className="bg-red-50 text-red-600 border-red-200 border text-xs">Pasif</Badge>}
                  </div>
                  {(loc.contact_person || loc.address) && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {loc.contact_person && `${loc.contact_person}`}
                      {loc.contact_person && loc.address && ' · '}
                      {loc.address}
                    </p>
                  )}
                </div>
                <div className="flex gap-1">
                  <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => { setEditingLoc(loc); setShowLocForm(true); }} data-testid={`edit-location-${loc.id}`}>
                    <Edit2 size={13} />
                  </Button>
                  <Button size="icon" variant="ghost" className={`h-7 w-7 ${loc.status === 'active' ? 'text-red-400 hover:text-red-600' : 'text-emerald-500 hover:text-emerald-700'}`}
                    onClick={() => handleLocStatusToggle(loc)} data-testid={`toggle-location-${loc.id}`}>
                    {loc.status === 'active' ? <XCircle size={13} /> : <CheckCircle size={13} />}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <CustomerFormModal
        open={showEditCustomer}
        onClose={() => setShowEditCustomer(false)}
        onSaved={onRefresh}
        existing={customer}
      />
      <LocationFormModal
        open={showLocForm}
        onClose={() => { setShowLocForm(false); setEditingLoc(null); }}
        onSaved={loadLocations}
        customerPublicId={customer.public_id}
        existing={editingLoc}
      />
    </div>
  );
}

// ── Main Customers Page ───────────────────────────────────────────────────────

export default function Customers() {
  const { api } = useAuth();
  const [customers, setCustomers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, page_size: 30 });
      if (search) params.set('search', search);
      if (statusFilter && statusFilter !== 'all') params.set('status', statusFilter);
      const { data } = await api.get(`/api/customers/?${params}`);
      setCustomers(data.items);
      setTotal(data.total);
    } catch {
      toast.error('Müşteriler yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, [api, page, search, statusFilter]);

  useEffect(() => { load(); }, [load]);

  // Reset page on search/filter change
  useEffect(() => { setPage(1); }, [search, statusFilter]);

  const handleRefresh = () => {
    load();
    // refresh selected if open
    if (selectedCustomer) {
      api.get(`/api/customers/${selectedCustomer.public_id}`)
        .then(r => setSelectedCustomer(r.data))
        .catch(() => {});
    }
  };

  if (selectedCustomer) {
    return (
      <div className="max-w-4xl mx-auto">
        <CustomerDetail
          customer={selectedCustomer}
          onBack={() => setSelectedCustomer(null)}
          onRefresh={handleRefresh}
        />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Users size={20} className="text-primary" />
          </div>
          <div>
            <h1 className="page-title">Müşteri Yönetimi</h1>
            <p className="text-muted-foreground text-sm">{total} müşteri</p>
          </div>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2" data-testid="create-customer-btn">
          <Plus size={16} /> Yeni Müşteri
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder="Müşteri ara..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            data-testid="customer-search"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
              <X size={14} />
            </button>
          )}
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-32" data-testid="status-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Aktif</SelectItem>
            <SelectItem value="inactive">Pasif</SelectItem>
            <SelectItem value="all">Tümü</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* List */}
      <div className="bg-card border rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 flex justify-center">
            <Loader2 size={24} className="animate-spin text-muted-foreground" />
          </div>
        ) : customers.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <Users size={40} className="mx-auto mb-3 opacity-30" />
            <p className="font-medium">Müşteri bulunamadı</p>
            <p className="text-sm mt-1">Yeni bir müşteri oluşturun veya filtrelerinizi değiştirin.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Müşteri</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden md:table-cell">İletişim</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden lg:table-cell">Lokasyon</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Durum</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {customers.map(c => (
                <tr key={c.id} className="hover:bg-muted/20 cursor-pointer transition-colors" onClick={() => setSelectedCustomer(c)} data-testid={`customer-row-${c.id}`}>
                  <td className="px-4 py-3">
                    <div className="font-medium">{c.legal_name}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                      {c.display_name && <span>{c.display_name}</span>}
                      {c.code && <span className="font-mono bg-muted px-1 rounded">{c.code}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell text-muted-foreground">
                    {c.phone || c.email || '—'}
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <MapPin size={12} /> {c.location_count || 0}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ChevronRight size={16} className="text-muted-foreground inline" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {total > 30 && (
          <div className="flex items-center justify-between px-4 py-3 border-t text-sm">
            <span className="text-muted-foreground">{total} kayıt</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Önceki</Button>
              <Button size="sm" variant="outline" disabled={page * 30 >= total} onClick={() => setPage(p => p + 1)}>Sonraki</Button>
            </div>
          </div>
        )}
      </div>

      <CustomerFormModal open={showCreate} onClose={() => setShowCreate(false)} onSaved={load} />
    </div>
  );
}
