import React, { useState, useEffect } from 'react';
import { Layers, Lock } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';

const MODULE_ICONS = {
  core: '⚙️', catering: '🍽️', customers: '👥', cash_bank: '🏦',
  cheques: '📋', loans: '💰', inventory: '📦', purchasing: '🛒',
  cost_accounting: '📊', employees: '👷', attendance: '✅', payroll: '💵',
  vehicles: '🚛', documents: '📁', advisor: '🧑‍💼', reports: '📈',
};

export default function Modules() {
  const { api } = useAuth();
  const { t } = useLanguage();
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(null);

  const load = async () => {
    try {
      const { data } = await api.get('/api/modules/');
      setModules(data);
    } catch { toast.error('Modüller yüklenemedi'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const toggle = async (module) => {
    if (module.module.is_core) return;
    setToggling(module.module.code);
    try {
      await api.put(`/api/modules/${module.module.code}/toggle`);
      toast.success(t('modules.toggleSuccess'));
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Hata'); }
    finally { setToggling(null); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Layers size={20} className="text-primary" />
        </div>
        <div>
          <h1 className="page-title">{t('modules.title')}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">Kiracınız için aktif iş modüllerini yönetin.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map((tm, i) => {
          const mod = tm.module;
          const enabled = tm.is_enabled;
          const isCore = mod.is_core;
          return (
            <div
              key={mod.code}
              className={`bg-card border rounded-xl p-4 transition-all animate-fadeInUp ${enabled ? 'border-primary/20 shadow-sm' : 'opacity-70'}`}
              style={{ animationDelay: `${i * 0.04}s` }}
              data-testid={`module-card-${mod.code}`}
            >
              <div className="flex items-start justify-between mb-3">
                <span className="text-2xl">{MODULE_ICONS[mod.code] || '📌'}</span>
                {isCore ? (
                  <Badge variant="outline" className="text-[10px] gap-1">
                    <Lock size={9} /> {t('modules.core')}
                  </Badge>
                ) : (
                  <button
                    onClick={() => toggle(tm)}
                    disabled={toggling === mod.code}
                    data-testid={`module-toggle-${mod.code}`}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${enabled ? 'bg-primary' : 'bg-muted'}`}
                  >
                    <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                  </button>
                )}
              </div>
              <h3 className="font-semibold text-sm">{mod.name_tr}</h3>
              <p className="text-xs text-muted-foreground mt-0.5">{mod.name_en}</p>
              {mod.description && <p className="text-xs text-muted-foreground mt-1.5">{mod.description}</p>}
              <div className="mt-3">
                <Badge
                  variant="outline"
                  className={`text-[10px] ${enabled ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-muted text-muted-foreground'}`}
                >
                  {enabled ? 'Aktif' : 'Pasif'}
                </Badge>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
