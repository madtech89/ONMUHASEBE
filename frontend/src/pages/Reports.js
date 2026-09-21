import React, { useState, useEffect, useCallback } from 'react';
import {
  FileBarChart2, Download, Loader2, Search,
  Calendar, FileText, FileSpreadsheet, Filter
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

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

export default function Reports() {
  const { api } = useAuth();
  const [customers, setCustomers] = useState([]);
  const [mealTypes, setMealTypes] = useState([]);
  const [dateFrom, setDateFrom] = useState(firstDay());
  const [dateTo, setDateTo] = useState(todayStr());
  const [customerId, setCustomerId] = useState('');
  const [mealTypeId, setMealTypeId] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState('');

  useEffect(() => {
    Promise.all([
      api.get('/api/customers/?page_size=100'),
      api.get('/api/prices/meal-types'),
    ]).then(([cr, mtr]) => {
      setCustomers(cr.data.items);
      setMealTypes(mtr.data);
    }).catch(() => {});
  }, [api]);

  const handleLoad = async () => {
    if (!dateFrom || !dateTo) { toast.error('Tarih aralığı seçin'); return; }
    if (dateFrom > dateTo) { toast.error('Başlangıç tarihi bitiş tarihinden büyük olamaz'); return; }
    setLoading(true);
    setReport(null);
    try {
      const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
      if (customerId) params.set('customer_id', customerId);
      if (mealTypeId) params.set('meal_type_id', mealTypeId);
      const { data } = await api.get(`/api/reports/meals?${params}`);
      setReport(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Rapor yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    setExporting(format);
    try {
      const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
      if (customerId) params.set('customer_id', customerId);
      const url = `${API}/api/reports/meals/${format}?${params}`;
      const resp = await fetch(url, { credentials: 'include', headers: { 'X-Tenant-ID': document.cookie.match(/activeTenant=([^;]+)/)?.[1] || '' } });
      if (!resp.ok) { toast.error('Dışa aktarma hatası'); return; }
      const blob = await resp.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `yemek_raporu_${dateFrom}_${dateTo}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      toast.error('Dışa aktarma sırasında hata oluştu');
    } finally {
      setExporting('');
    }
  };

  const handleExportWithAuth = async (format) => {
    setExporting(format);
    try {
      const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
      if (customerId) params.set('customer_id', customerId);
      const { data: blob } = await api.get(`/api/reports/meals/${format}?${params}`, { responseType: 'blob' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `yemek_raporu_${dateFrom}_${dateTo}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success('Dosya indiriliyor...');
    } catch {
      toast.error('Dışa aktarma sırasında hata oluştu');
    } finally {
      setExporting('');
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <FileBarChart2 size={20} className="text-primary" />
        </div>
        <div>
          <h1 className="page-title">Yemek Raporları</h1>
          <p className="text-muted-foreground text-sm">Tarih aralıklı yemek özet raporu</p>
        </div>
      </div>

      {/* Filter Form */}
      <div className="bg-card border rounded-xl p-5 space-y-4">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <Filter size={14} /> Rapor Kriterleri
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <Label className="text-xs">Başlangıç Tarihi <span className="text-red-500">*</span></Label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="mt-1 w-full h-9 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              data-testid="report-date-from"
            />
          </div>
          <div>
            <Label className="text-xs">Bitiş Tarihi <span className="text-red-500">*</span></Label>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="mt-1 w-full h-9 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              data-testid="report-date-to"
            />
          </div>
          <div>
            <Label className="text-xs">Müşteri (isteğe bağlı)</Label>
            <Select value={customerId || 'all'} onValueChange={v => setCustomerId(v === 'all' ? '' : v)}>
              <SelectTrigger className="mt-1 h-9 text-sm" data-testid="report-customer-filter">
                <SelectValue placeholder="Tüm müşteriler" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm müşteriler</SelectItem>
                {customers.map(c => <SelectItem key={c.id} value={String(c.id)}>{c.legal_name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Yemek Tipi (isteğe bağlı)</Label>
            <Select value={mealTypeId || 'all'} onValueChange={v => setMealTypeId(v === 'all' ? '' : v)}>
              <SelectTrigger className="mt-1 h-9 text-sm" data-testid="report-meal-type-filter">
                <SelectValue placeholder="Tüm yemekler" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm yemekler</SelectItem>
                {mealTypes.map(mt => <SelectItem key={mt.id} value={String(mt.id)}>{mt.name_tr}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button onClick={handleLoad} disabled={loading} className="gap-2" data-testid="load-report-btn">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <FileBarChart2 size={14} />}
            Raporu Getir
          </Button>
          {report && (
            <>
              <Button
                variant="outline"
                onClick={() => handleExportWithAuth('pdf')}
                disabled={!!exporting}
                className="gap-2"
                data-testid="export-pdf-btn"
              >
                {exporting === 'pdf' ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} className="text-red-500" />}
                PDF İndir
              </Button>
              <Button
                variant="outline"
                onClick={() => handleExportWithAuth('excel')}
                disabled={!!exporting}
                className="gap-2"
                data-testid="export-excel-btn"
              >
                {exporting === 'excel' ? <Loader2 size={14} className="animate-spin" /> : <FileSpreadsheet size={14} className="text-emerald-600" />}
                Excel İndir
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Report Results */}
      {report && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-card border rounded-xl p-4">
              <div className="text-xs text-muted-foreground">Toplam Porsiyon</div>
              <div className="text-xl font-bold mt-1 font-mono">{parseFloat(report.summary.total_quantity || 0).toLocaleString('tr-TR')}</div>
            </div>
            <div className="bg-card border rounded-xl p-4">
              <div className="text-xs text-muted-foreground">Net Tutar</div>
              <div className="text-xl font-bold mt-1 font-mono">₺{fmtAmount(report.summary.total_net)}</div>
            </div>
            <div className="bg-card border rounded-xl p-4">
              <div className="text-xs text-muted-foreground">KDV</div>
              <div className="text-xl font-bold mt-1 font-mono">₺{fmtAmount(report.summary.total_vat)}</div>
            </div>
            <div className="bg-card border rounded-xl p-4 bg-primary/5 border-primary/30">
              <div className="text-xs text-muted-foreground">Brüt Toplam</div>
              <div className="text-xl font-bold mt-1 font-mono text-primary">₺{fmtAmount(report.summary.total_gross)}</div>
            </div>
          </div>

          {/* By Meal Type Summary */}
          {report.summary.by_meal_type && Object.keys(report.summary.by_meal_type).length > 0 && (
            <div className="bg-card border rounded-xl p-5">
              <h3 className="font-semibold text-sm mb-3">Yemek Tipine Göre Özet</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(report.summary.by_meal_type).map(([code, item]) => (
                  <div key={code} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                    <div>
                      <div className="font-medium text-sm">{item.name}</div>
                      <div className="text-xs text-muted-foreground">{parseFloat(item.qty || 0).toLocaleString('tr-TR')} porsiyon</div>
                    </div>
                    <div className="text-right font-mono text-sm font-semibold">₺{fmtAmount(item.gross)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rows Table */}
          <div className="bg-card border rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b flex items-center justify-between">
              <h3 className="font-semibold text-sm">Detay Listesi</h3>
              <span className="text-xs text-muted-foreground">{report.rows.length} satır</span>
            </div>
            {report.rows.length === 0 ? (
              <div className="p-10 text-center text-muted-foreground">
                <FileBarChart2 size={36} className="mx-auto mb-2 opacity-30" />
                <p>Bu kriterlere uygun kayıt bulunamadı</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/30">
                      <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Tarih</th>
                      <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Müşteri</th>
                      <th className="text-left px-4 py-2.5 font-medium text-muted-foreground hidden md:table-cell">Lokasyon</th>
                      <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Yemek</th>
                      <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">Adet</th>
                      <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">Birim</th>
                      <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">Net</th>
                      <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">Brüt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {report.rows.map((row, i) => (
                      <tr key={i} className="hover:bg-muted/20" data-testid={`report-row-${i}`}>
                        <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">{fmtDate(row.business_date)}</td>
                        <td className="px-4 py-2.5 font-medium">{row.customer_name}</td>
                        <td className="px-4 py-2.5 hidden md:table-cell text-muted-foreground">{row.location_name || '—'}</td>
                        <td className="px-4 py-2.5">{row.meal_type_name}</td>
                        <td className="px-4 py-2.5 text-right font-mono">{parseFloat(row.total_quantity).toLocaleString('tr-TR')}</td>
                        <td className="px-4 py-2.5 text-right font-mono text-xs text-muted-foreground">₺{fmtAmount(row.unit_price)}</td>
                        <td className="px-4 py-2.5 text-right font-mono">₺{fmtAmount(row.total_net)}</td>
                        <td className="px-4 py-2.5 text-right font-mono font-medium">₺{fmtAmount(row.total_gross)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 bg-muted/20">
                      <td colSpan={6} className="px-4 py-3 font-semibold text-right">TOPLAM</td>
                      <td className="px-4 py-3 text-right font-mono font-semibold">₺{fmtAmount(report.summary.total_net)}</td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-primary">₺{fmtAmount(report.summary.total_gross)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
