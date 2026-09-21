import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  UtensilsCrossed, Search, Calendar, ChevronDown, CheckCircle2,
  Loader2, X, RefreshCw, ClipboardList, AlertCircle
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';

function today() {
  return new Date().toISOString().slice(0, 10);
}

function genKey() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

// ── Location Search Combobox ─────────────────────────────────────────────────

function LocationSearch({ onSelect, selectedDisplay }) {
  const { api } = useAuth();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);

  const search = useCallback(async (q) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/api/customers/search/locations?q=${encodeURIComponent(q)}`);
      setResults(data);
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    const timer = setTimeout(() => { if (query.length >= 0) search(query); }, 200);
    return () => clearTimeout(timer);
  }, [query, search]);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSelect = (item) => {
    onSelect(item);
    setOpen(false);
    setQuery('');
  };

  return (
    <div ref={ref} className="relative">
      <Label>Müşteri / Lokasyon <span className="text-red-500">*</span></Label>
      {selectedDisplay ? (
        <div className="flex items-center gap-2 mt-1 p-2.5 rounded-lg border bg-primary/5 border-primary/30">
          <CheckCircle2 size={16} className="text-primary flex-shrink-0" />
          <span className="text-sm font-medium flex-1">{selectedDisplay}</span>
          <button onClick={() => onSelect(null)} className="text-muted-foreground hover:text-foreground">
            <X size={14} />
          </button>
        </div>
      ) : (
        <>
          <div className="relative mt-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-8"
              placeholder="Müşteri veya lokasyon adı yazın..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onFocus={() => search(query)}
              data-testid="location-search-input"
              autoComplete="off"
            />
            {loading && <Loader2 size={14} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-muted-foreground" />}
          </div>
          {open && results.length > 0 && (
            <div className="absolute z-20 mt-1 w-full bg-popover border rounded-xl shadow-lg max-h-56 overflow-y-auto">
              {results.map((r, i) => (
                <button
                  key={i}
                  onClick={() => handleSelect(r)}
                  className="w-full text-left px-4 py-2.5 hover:bg-muted text-sm transition-colors"
                  data-testid={`location-result-${i}`}
                >
                  <div className="font-medium">{r.customer_name}</div>
                  <div className="text-xs text-muted-foreground">{r.location_name} · {r.location_type}</div>
                </button>
              ))}
            </div>
          )}
          {open && !loading && results.length === 0 && query.length > 0 && (
            <div className="absolute z-20 mt-1 w-full bg-popover border rounded-xl shadow-lg p-4 text-center text-sm text-muted-foreground">
              Sonuç bulunamadı
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Daily Summary Table ───────────────────────────────────────────────────────

function DailySummary({ date, onRefresh }) {
  const { api } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data: d } = await api.get(`/api/meal-entries/daily?business_date=${date}`);
      setData(d);
    } catch {
      toast.error('Günlük özet yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, [api, date]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="p-8 flex justify-center"><Loader2 size={20} className="animate-spin text-muted-foreground" /></div>;
  if (!data || data.aggregates.length === 0) return (
    <div className="p-8 text-center text-muted-foreground text-sm">
      <ClipboardList size={32} className="mx-auto mb-2 opacity-30" />
      Bu tarihte yemek girişi bulunmuyor
    </div>
  );

  const fmtDate = (d) => {
    const [y, m, day] = d.split('-');
    return `${day}.${m}.${y}`;
  };

  return (
    <div className="overflow-x-auto">
      <div className="flex items-center justify-between px-5 py-3 border-b">
        <h3 className="font-semibold text-sm">{fmtDate(date)} — Günlük Özet</h3>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>Toplam Brüt: <span className="font-semibold text-foreground">₺{parseFloat(data.grand_total_gross).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</span></span>
          <button onClick={load} className="text-primary hover:text-primary/70">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/30">
            <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Müşteri / Lokasyon</th>
            {data.aggregates[0]?.items?.map(item => (
              <th key={item.meal_type_id} className="text-center px-3 py-2.5 font-medium text-muted-foreground">{item.meal_type_name}</th>
            ))}
            <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">Brüt Tutar</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {data.aggregates.map((agg, i) => (
            <tr key={i} className="hover:bg-muted/20">
              <td className="px-4 py-2.5">
                <div className="font-medium">{agg.customer_name}</div>
                {agg.location_name && <div className="text-xs text-muted-foreground">{agg.location_name}</div>}
              </td>
              {agg.items.map(item => (
                <td key={item.meal_type_id} className="px-3 py-2.5 text-center">
                  {parseFloat(item.total_quantity) > 0 ? (
                    <span className="font-mono font-medium">{parseFloat(item.total_quantity).toLocaleString('tr-TR')}</span>
                  ) : <span className="text-muted-foreground">—</span>}
                </td>
              ))}
              <td className="px-4 py-2.5 text-right font-mono text-sm">
                ₺{parseFloat(agg.total_gross).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main MealEntry Page ───────────────────────────────────────────────────────

export default function MealEntry() {
  const { api } = useAuth();
  const [mealTypes, setMealTypes] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [businessDate, setBusinessDate] = useState(today());
  const [quantities, setQuantities] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(genKey());
  const [activeTab, setActiveTab] = useState('entry'); // 'entry' | 'summary'
  const [summaryDate, setSummaryDate] = useState(today());

  useEffect(() => {
    api.get('/api/prices/meal-types')
      .then(r => {
        setMealTypes(r.data);
        const initial = {};
        r.data.forEach(mt => { initial[String(mt.id)] = ''; });
        setQuantities(initial);
      })
      .catch(() => toast.error('Yemek tipleri yüklenemedi'));
  }, [api]);

  const handleSelectLocation = (item) => {
    setSelectedLocation(item);
    setIdempotencyKey(genKey());
  };

  const handleQuantityChange = (mealTypeId, value) => {
    if (value !== '' && !/^\d*\.?\d*$/.test(value)) return;
    setQuantities(prev => ({ ...prev, [String(mealTypeId)]: value }));
  };

  const handleKeyDown = (e, idx) => {
    if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      const inputs = document.querySelectorAll('[data-meal-input]');
      const next = inputs[idx + 1];
      if (next) next.focus();
      else if (e.key === 'Enter') handleSubmit();
    }
  };

  const hasAnyQty = Object.values(quantities).some(v => v !== '' && parseFloat(v) > 0);

  const handleSubmit = async () => {
    if (!selectedLocation) { toast.error('Müşteri/Lokasyon seçin'); return; }
    if (!businessDate) { toast.error('Tarih seçin'); return; }
    if (!hasAnyQty) { toast.error('En az bir yemek miktarı girin'); return; }

    const qtyPayload = {};
    Object.entries(quantities).forEach(([k, v]) => {
      if (v !== '' && parseFloat(v) > 0) qtyPayload[k] = parseFloat(v);
    });

    setSubmitting(true);
    try {
      await api.post('/api/meal-entries/', {
        customer_id: selectedLocation.customer_id,
        location_id: selectedLocation.location_id || null,
        business_date: businessDate,
        quantities: qtyPayload,
        idempotency_key: idempotencyKey,
      });
      toast.success('Yemek girişi kaydedildi');
      // Reset for next entry
      const reset = {};
      mealTypes.forEach(mt => { reset[String(mt.id)] = ''; });
      setQuantities(reset);
      setIdempotencyKey(genKey());
      // Auto-switch to summary
      setSummaryDate(businessDate);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (typeof detail === 'string') toast.error(detail);
      else toast.error('Kayıt sırasında hata oluştu');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setSelectedLocation(null);
    const reset = {};
    mealTypes.forEach(mt => { reset[String(mt.id)] = ''; });
    setQuantities(reset);
    setIdempotencyKey(genKey());
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <UtensilsCrossed size={20} className="text-primary" />
        </div>
        <div>
          <h1 className="page-title">Yemek Girişi</h1>
          <p className="text-muted-foreground text-sm">Günlük yemek miktarı kaydet</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-muted/50 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab('entry')}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'entry' ? 'bg-white shadow text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
          data-testid="tab-entry"
        >
          Yeni Giriş
        </button>
        <button
          onClick={() => setActiveTab('summary')}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'summary' ? 'bg-white shadow text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
          data-testid="tab-summary"
        >
          Günlük Özet
        </button>
      </div>

      {activeTab === 'entry' && (
        <div className="bg-card border rounded-xl p-6 space-y-6">
          {/* Step 1: Select location */}
          <LocationSearch onSelect={handleSelectLocation} selectedDisplay={selectedLocation?.display} />

          {/* Step 2: Date */}
          <div>
            <Label htmlFor="business-date">İş Tarihi <span className="text-red-500">*</span></Label>
            <div className="relative mt-1 w-48">
              <Calendar size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                id="business-date"
                type="date"
                value={businessDate}
                onChange={e => setBusinessDate(e.target.value)}
                className="w-full pl-8 h-10 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                data-testid="business-date-input"
              />
            </div>
          </div>

          {/* Step 3: Quantities */}
          {selectedLocation && (
            <div>
              <Label>Yemek Miktarları</Label>
              <div className="mt-2 grid grid-cols-2 md:grid-cols-3 gap-3">
                {mealTypes.map((mt, idx) => (
                  <div key={mt.id} className="space-y-1">
                    <Label className="text-xs text-muted-foreground">{mt.name_tr}</Label>
                    <Input
                      type="text"
                      inputMode="decimal"
                      value={quantities[String(mt.id)] || ''}
                      onChange={e => handleQuantityChange(mt.id, e.target.value)}
                      onKeyDown={e => handleKeyDown(e, idx)}
                      placeholder="0"
                      className="text-center font-mono"
                      data-meal-input
                      data-testid={`qty-${mt.code}`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {!selectedLocation && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground p-3 bg-muted/30 rounded-lg">
              <AlertCircle size={16} />
              Müşteri/lokasyon seçtikten sonra yemek miktarlarını girebilirsiniz
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t">
            <Button type="button" variant="ghost" size="sm" onClick={handleReset} className="text-muted-foreground">
              <X size={14} className="mr-1" /> Temizle
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting || !selectedLocation || !hasAnyQty}
              className="gap-2"
              data-testid="submit-meal-entry-btn"
            >
              {submitting ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={16} />}
              Kaydet
            </Button>
          </div>
        </div>
      )}

      {activeTab === 'summary' && (
        <div className="bg-card border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b flex items-center gap-3">
            <Label>Tarih:</Label>
            <input
              type="date"
              value={summaryDate}
              onChange={e => setSummaryDate(e.target.value)}
              className="h-9 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              data-testid="summary-date-input"
            />
          </div>
          <DailySummary date={summaryDate} />
        </div>
      )}
    </div>
  );
}
