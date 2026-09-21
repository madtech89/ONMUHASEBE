import React, { useState, useEffect, useCallback } from 'react';
import {
  CreditCard, Search, Loader2, ChevronDown, Calendar,
  TrendingUp, TrendingDown, ArrowLeftRight, ArrowLeft
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';

function fmtDate(d) {
  if (!d) return '—';
  const [y, m, day] = String(d).split('-');
  return `${day}.${m}.${y}`;
}

function fmtAmount(v) {
  return parseFloat(v || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2 });
}

function firstDay() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

// ── Ledger Statement ──────────────────────────────────────────────────────────

function LedgerStatement({ customerId, customerName, onBack }) {
  const { api } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState(firstDay());
  const [dateTo, setDateTo] = useState(todayStr());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      const { data: d } = await api.get(`/api/ledger/customer/${customerId}?${params}`);
      setData(d);
    } catch {
      toast.error('Hesap ekstresi yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, [api, customerId, dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6" data-testid="ledger-statement">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1 text-muted-foreground hover:text-foreground text-sm">
          <ArrowLeft size={16} /> Müşteri Listesi
        </button>
      </div>

      <div className="flex items-center gap-3">
        <CreditCard size={18} className="text-primary" />
        <div>
          <h2 className="font-semibold">{customerName}</h2>
          <p className="text-sm text-muted-foreground">Hesap Ekstresi</p>
        </div>
      </div>

      {/* Date Filter */}
      <div className="flex gap-3 flex-wrap items-end">
        <div>
          <Label className="text-xs text-muted-foreground">Başlangıç</Label>
          <input
            type="date"
            value={dateFrom}
            onChange={e => setDateFrom(e.target.value)}
            className="h-9 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            data-testid="ledger-date-from"
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">Bitiş</Label>
          <input
            type="date"
            value={dateTo}
            onChange={e => setDateTo(e.target.value)}
            className="h-9 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            data-testid="ledger-date-to"
          />
        </div>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-card border rounded-xl p-4">
            <div className="text-xs text-muted-foreground mb-1">Açılış Bakiyesi</div>
            <div className="text-base font-semibold font-mono">₺{fmtAmount(data.opening_balance)}</div>
          </div>
          <div className="bg-card border rounded-xl p-4">
            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
              <TrendingUp size={12} className="text-red-500" /> Dönem Borç
            </div>
            <div className="text-base font-semibold font-mono text-red-600">₺{fmtAmount(data.period_debit)}</div>
          </div>
          <div className="bg-card border rounded-xl p-4">
            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
              <TrendingDown size={12} className="text-emerald-500" /> Dönem Alacak
            </div>
            <div className="text-base font-semibold font-mono text-emerald-600">₺{fmtAmount(data.period_credit)}</div>
          </div>
          <div className="bg-card border rounded-xl p-4">
            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
              <ArrowLeftRight size={12} /> Kapanış Bakiyesi
            </div>
            <div className={`text-base font-semibold font-mono ${parseFloat(data.closing_balance) > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              ₺{fmtAmount(data.closing_balance)}
            </div>
          </div>
        </div>
      )}

      {/* Entries Table */}
      <div className="bg-card border rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b flex items-center justify-between">
          <h3 className="font-semibold text-sm">Hareket Listesi</h3>
          {data && <span className="text-xs text-muted-foreground">{data.entries.length} kayıt</span>}
        </div>
        {loading ? (
          <div className="p-8 flex justify-center"><Loader2 size={20} className="animate-spin text-muted-foreground" /></div>
        ) : !data || data.entries.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground text-sm">
            <ArrowLeftRight size={32} className="mx-auto mb-2 opacity-30" />
            Bu dönemde hareket bulunmuyor
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Tarih</th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Açıklama</th>
                  <th className="text-right px-4 py-2.5 font-medium text-muted-foreground text-red-600">Borç</th>
                  <th className="text-right px-4 py-2.5 font-medium text-muted-foreground text-emerald-600">Alacak</th>
                  <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">Tür</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.entries.map((entry, i) => (
                  <tr key={entry.id || i} className="hover:bg-muted/20" data-testid={`ledger-entry-${i}`}>
                    <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">{fmtDate(entry.business_date)}</td>
                    <td className="px-4 py-2.5">{entry.description || '—'}</td>
                    <td className="px-4 py-2.5 text-right font-mono">
                      {parseFloat(entry.debit_amount) > 0 ? (
                        <span className="text-red-600">₺{fmtAmount(entry.debit_amount)}</span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono">
                      {parseFloat(entry.credit_amount) > 0 ? (
                        <span className="text-emerald-600">₺{fmtAmount(entry.credit_amount)}</span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <span className="text-xs bg-muted px-2 py-0.5 rounded font-mono">{entry.source_type || 'manuel'}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Ledger Page ──────────────────────────────────────────────────────────

export default function Ledger() {
  const { api } = useAuth();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState(null);

  useEffect(() => {
    api.get('/api/customers/?page_size=100&status=active')
      .then(r => setCustomers(r.data.items))
      .catch(() => toast.error('Müşteriler yüklenemedi'))
      .finally(() => setLoading(false));
  }, [api]);

  const filtered = customers.filter(c =>
    c.legal_name.toLowerCase().includes(search.toLowerCase()) ||
    (c.display_name || '').toLowerCase().includes(search.toLowerCase())
  );

  if (selectedCustomer) {
    return (
      <div className="max-w-5xl mx-auto">
        <LedgerStatement
          customerId={selectedCustomer.id}
          customerName={selectedCustomer.legal_name}
          onBack={() => setSelectedCustomer(null)}
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <CreditCard size={20} className="text-primary" />
        </div>
        <div>
          <h1 className="page-title">Cari Hesaplar</h1>
          <p className="text-muted-foreground text-sm">Müşteri bazlı borç/alacak ekstresi</p>
        </div>
      </div>

      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input className="pl-8" placeholder="Müşteri ara..." value={search} onChange={e => setSearch(e.target.value)} data-testid="ledger-customer-search" />
      </div>

      <div className="bg-card border rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 flex justify-center"><Loader2 size={20} className="animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground">
            <CreditCard size={36} className="mx-auto mb-2 opacity-30" />
            <p>Müşteri bulunamadı</p>
          </div>
        ) : (
          <div className="divide-y">
            {filtered.map(c => (
              <button
                key={c.id}
                onClick={() => setSelectedCustomer(c)}
                className="w-full text-left flex items-center gap-3 px-5 py-3.5 hover:bg-muted/30 transition-colors"
                data-testid={`ledger-customer-row-${c.id}`}
              >
                <div className="flex-1">
                  <div className="font-medium text-sm">{c.legal_name}</div>
                  {c.code && <div className="text-xs text-muted-foreground font-mono">{c.code}</div>}
                </div>
                <ChevronDown size={16} className="text-muted-foreground -rotate-90" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
