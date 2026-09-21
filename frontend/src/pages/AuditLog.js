import React, { useState, useEffect, useCallback } from 'react';
import { ClipboardList, Filter, X, ChevronDown, ChevronUp } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';

const SEVERITY_STYLES = {
  critical: 'bg-red-50 text-red-700 border-red-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  info: 'bg-blue-50 text-blue-700 border-blue-200',
};

const PAGE_SIZE = 50;

function ExpandableRow({ log }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = log.old_value || log.new_value || log.description;

  return (
    <>
      <tr
        className="cursor-pointer"
        onClick={() => hasDetails && setExpanded(e => !e)}
        data-testid={`audit-row-${log.id}`}
      >
        <td>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={`text-[10px] ${SEVERITY_STYLES[log.severity] || 'bg-muted text-muted-foreground'}`}>
              {log.severity}
            </Badge>
          </div>
        </td>
        <td>
          <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">{log.action_type}</code>
        </td>
        <td className="text-xs text-muted-foreground">{log.user_email || '—'}</td>
        <td className="text-xs text-muted-foreground">{log.ip_address || '—'}</td>
        <td className="text-xs text-muted-foreground">
          {log.entity_type && (
            <span className="font-mono">{log.entity_type}{log.entity_id ? `:${log.entity_id.slice(0, 8)}` : ''}</span>
          )}
        </td>
        <td className="text-xs text-muted-foreground whitespace-nowrap">
          {log.created_at ? new Date(log.created_at).toLocaleString('tr') : '—'}
        </td>
        <td>
          {hasDetails && (
            <button className="text-muted-foreground hover:text-foreground">
              {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
        </td>
      </tr>
      {expanded && hasDetails && (
        <tr>
          <td colSpan={7} className="bg-muted/40 px-4 py-3">
            <div className="space-y-2 text-xs">
              {log.description && (
                <p className="text-foreground"><span className="font-semibold">Açıklama: </span>{log.description}</p>
              )}
              {log.old_value && (
                <div>
                  <span className="font-semibold text-amber-700">Önceki:</span>
                  <pre className="mt-1 text-[10px] bg-amber-50 border border-amber-200 rounded p-2 overflow-auto max-h-24">
                    {JSON.stringify(log.old_value, null, 2)}
                  </pre>
                </div>
              )}
              {log.new_value && (
                <div>
                  <span className="font-semibold text-emerald-700">Sonraki:</span>
                  <pre className="mt-1 text-[10px] bg-emerald-50 border border-emerald-200 rounded p-2 overflow-auto max-h-24">
                    {JSON.stringify(log.new_value, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AuditLog() {
  const { api } = useAuth();
  const { t } = useLanguage();

  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [filters, setFilters] = useState({ action_type: '', severity: '', user_email: '' });
  const [pendingFilters, setPendingFilters] = useState({ action_type: '', severity: '', user_email: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, page_size: PAGE_SIZE });
      if (filters.action_type) params.append('action_type', filters.action_type);
      if (filters.severity) params.append('severity', filters.severity);
      if (filters.user_email) params.append('user_email', filters.user_email);
      const { data } = await api.get(`/api/audit/?${params}`);
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch {
      toast.error('Audit log yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, [api, page, filters]);

  useEffect(() => { load(); }, [load]);

  const applyFilters = () => { setFilters({ ...pendingFilters }); setPage(1); };
  const clearFilters = () => {
    const empty = { action_type: '', severity: '', user_email: '' };
    setPendingFilters(empty);
    setFilters(empty);
    setPage(1);
  };

  const hasActiveFilters = filters.action_type || filters.severity || filters.user_email;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <ClipboardList size={20} className="text-primary" />
        </div>
        <div>
          <h1 className="page-title">{t('audit.title')}</h1>
          <p className="text-xs text-muted-foreground mt-0.5">{total} kayıt</p>
        </div>
      </div>

      {/* Filter bar */}
      <div className="bg-card border rounded-xl p-4 space-y-3" data-testid="audit-filters">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Filter size={14} /> Filtreler
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">İşlem Tipi</label>
            <Input
              placeholder="user.login, document.uploaded..."
              value={pendingFilters.action_type}
              onChange={e => setPendingFilters(f => ({ ...f, action_type: e.target.value }))}
              className="h-8 text-sm"
              data-testid="audit-filter-action"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Önem Seviyesi</label>
            <Select
              value={pendingFilters.severity || 'all'}
              onValueChange={v => setPendingFilters(f => ({ ...f, severity: v === 'all' ? '' : v }))}
            >
              <SelectTrigger className="h-8 text-sm" data-testid="audit-filter-severity">
                <SelectValue placeholder="Tümü" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tümü</SelectItem>
                <SelectItem value="info">Bilgi</SelectItem>
                <SelectItem value="warning">Uyarı</SelectItem>
                <SelectItem value="critical">Kritik</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Kullanıcı E-posta</label>
            <Input
              placeholder="user@example.com"
              value={pendingFilters.user_email}
              onChange={e => setPendingFilters(f => ({ ...f, user_email: e.target.value }))}
              className="h-8 text-sm"
              data-testid="audit-filter-email"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={applyFilters} data-testid="audit-apply-filters-btn">Filtrele</Button>
          {hasActiveFilters && (
            <Button size="sm" variant="ghost" onClick={clearFilters} className="gap-1 text-muted-foreground" data-testid="audit-clear-filters-btn">
              <X size={12} /> Temizle
            </Button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : logs.length === 0 ? (
          <p className="text-center text-muted-foreground text-sm py-16">{t('audit.noLogs')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full data-table">
              <thead>
                <tr>
                  <th className="text-left w-24">Seviye</th>
                  <th className="text-left">İşlem</th>
                  <th className="text-left">Kullanıcı</th>
                  <th className="text-left">IP</th>
                  <th className="text-left">Varlık</th>
                  <th className="text-left w-36">Zaman</th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody>
                {logs.map(log => <ExpandableRow key={log.id} log={log} />)}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t text-xs text-muted-foreground">
            <span>{total} kayıttan {Math.min((page - 1) * PAGE_SIZE + 1, total)}–{Math.min(page * PAGE_SIZE, total)} gösteriliyor</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Önceki</Button>
              <Button size="sm" variant="outline" disabled={page * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>Sonraki</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
