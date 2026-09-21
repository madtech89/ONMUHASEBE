import React, { useState, useEffect, useRef, useCallback } from 'react';
import { FolderOpen, Upload, Download, Trash2, Eye, Filter, X, FileText, Image, File } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';

const CATEGORIES = [
  { value: 'fatura', label: 'Fatura' },
  { value: 'irsaliye', label: 'İrsaliye' },
  { value: 'sozlesme', label: 'Sözleşme' },
  { value: 'arac_belgesi', label: 'Araç Belgesi' },
  { value: 'personel_belgesi', label: 'Personel Belgesi' },
  { value: 'cek', label: 'Çek' },
  { value: 'diger', label: 'Diğer' },
];

function formatBytes(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function FileIcon({ mimeType }) {
  if (mimeType?.startsWith('image/')) return <Image size={16} className="text-blue-500" />;
  if (mimeType === 'application/pdf') return <FileText size={16} className="text-red-500" />;
  return <File size={16} className="text-muted-foreground" />;
}

function PreviewModal({ doc, onClose, onDownload }) {
  const isImage = doc?.mime_type?.startsWith('image/');
  const isPdf = doc?.mime_type === 'application/pdf';

  return (
    <Dialog open={!!doc} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col" data-testid="preview-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-sm font-semibold truncate pr-8">
            <FileIcon mimeType={doc?.mime_type} />
            {doc?.original_filename}
          </DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-auto min-h-0 flex items-center justify-center bg-muted rounded-lg p-4">
          {isImage ? (
            <img
              src={`${process.env.REACT_APP_BACKEND_URL}/api/documents/${doc?.public_id}/download`}
              alt={doc?.original_filename}
              className="max-w-full max-h-[60vh] object-contain rounded"
            />
          ) : isPdf ? (
            <div className="flex flex-col items-center gap-3 text-muted-foreground">
              <FileText size={48} className="text-red-400" />
              <p className="text-sm">PDF önizleme için indirin</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 text-muted-foreground">
              <File size={48} />
              <p className="text-sm">Bu dosya türü için önizleme desteklenmiyor</p>
            </div>
          )}
        </div>
        <div className="flex items-center justify-between pt-3 border-t text-xs text-muted-foreground">
          <div className="flex gap-4">
            <span><span className="font-medium">Boyut:</span> {formatBytes(doc?.file_size)}</span>
            <span><span className="font-medium">MIME:</span> {doc?.mime_type}</span>
            {doc?.category && (
              <span><span className="font-medium">Kategori:</span> {CATEGORIES.find(c => c.value === doc.category)?.label || doc.category}</span>
            )}
          </div>
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => onDownload(doc)} data-testid="preview-download-btn">
            <Download size={14} /> İndir
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function Documents() {
  const { api } = useAuth();
  const { t } = useLanguage();

  const [docs, setDocs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [filterCategory, setFilterCategory] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadForm, setUploadForm] = useState({ category: '', file: null });
  const fileInputRef = useRef();
  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, page_size: PAGE_SIZE });
      if (filterCategory) params.append('category', filterCategory);
      const { data } = await api.get(`/api/documents/?${params}`);
      setDocs(data.items || []);
      setTotal(data.total || 0);
    } catch {
      toast.error('Belgeler yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, [api, page, filterCategory]);

  useEffect(() => { load(); }, [load]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadForm.file) { toast.error('Lütfen dosya seçin'); return; }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', uploadForm.file);
      if (uploadForm.category) fd.append('category', uploadForm.category);
      await api.post('/api/documents/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success('Belge yüklendi');
      setShowUpload(false);
      setUploadForm({ category: '', file: null });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Yükleme hatası');
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (doc) => {
    try {
      const resp = await api.get(`/api/documents/${doc.public_id}/download`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([resp.data], { type: doc.mime_type }));
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.original_filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('İndirme başarısız');
    }
  };

  const handleDelete = async (doc) => {
    if (!window.confirm(`"${doc.original_filename}" arşivlensin mi?`)) return;
    try {
      await api.delete(`/api/documents/${doc.public_id}`);
      toast.success('Belge arşivlendi');
      load();
    } catch {
      toast.error('Silme hatası');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) { setUploadForm(f => ({ ...f, file })); setShowUpload(true); }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <FolderOpen size={20} className="text-primary" />
          </div>
          <div>
            <h1 className="page-title">{t('documents.title')}</h1>
            <p className="text-xs text-muted-foreground mt-0.5">{total} belge</p>
          </div>
        </div>
        <Button onClick={() => setShowUpload(true)} className="gap-2" data-testid="upload-doc-btn">
          <Upload size={16} /> {t('documents.upload')}
        </Button>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 bg-card border rounded-xl px-4 py-3">
        <Filter size={15} className="text-muted-foreground flex-shrink-0" />
        <Select value={filterCategory || 'all'} onValueChange={v => { setFilterCategory(v === 'all' ? '' : v); setPage(1); }}>
          <SelectTrigger className="w-48 h-8 text-sm" data-testid="doc-category-filter">
            <SelectValue placeholder="Tüm kategoriler" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tüm kategoriler</SelectItem>
            {CATEGORIES.map(c => (
              <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {filterCategory && (
          <button onClick={() => setFilterCategory('')} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
            <X size={12} /> Temizle
          </button>
        )}
      </div>

      {/* Drop zone + table */}
      <div
        className={`bg-card border rounded-xl overflow-hidden transition-colors ${dragOver ? 'border-primary border-2 bg-primary/5' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        data-testid="documents-table-container"
      >
        {dragOver && (
          <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
            <div className="bg-primary/10 border-2 border-primary border-dashed rounded-xl p-8 text-primary font-semibold">
              Dosyayı buraya bırakın
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : docs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <FolderOpen size={40} className="text-muted-foreground/40" />
            <p className="text-muted-foreground text-sm">{t('documents.noDocuments')}</p>
            <Button size="sm" variant="outline" onClick={() => setShowUpload(true)} className="gap-1.5">
              <Upload size={13} /> İlk belgeyi yükle
            </Button>
          </div>
        ) : (
          <table className="w-full data-table">
            <thead>
              <tr>
                <th className="text-left">{t('documents.fileName')}</th>
                <th className="text-left">{t('documents.category')}</th>
                <th className="text-left">{t('documents.fileSize')}</th>
                <th className="text-left">{t('documents.uploadDate')}</th>
                <th className="text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc, i) => (
                <tr key={doc.public_id} data-testid={`doc-row-${i}`}>
                  <td>
                    <div className="flex items-center gap-2">
                      <FileIcon mimeType={doc.mime_type} />
                      <button
                        className="text-sm font-medium hover:text-primary hover:underline truncate max-w-xs text-left"
                        onClick={() => setPreviewDoc(doc)}
                        data-testid={`doc-preview-btn-${i}`}
                      >
                        {doc.original_filename}
                      </button>
                    </div>
                  </td>
                  <td>
                    {doc.category ? (
                      <Badge variant="outline" className="text-[10px]">
                        {CATEGORIES.find(c => c.value === doc.category)?.label || doc.category}
                      </Badge>
                    ) : <span className="text-xs text-muted-foreground">—</span>}
                  </td>
                  <td className="text-xs text-muted-foreground">{formatBytes(doc.file_size)}</td>
                  <td className="text-xs text-muted-foreground">
                    {doc.created_at ? new Date(doc.created_at).toLocaleDateString('tr') : '—'}
                  </td>
                  <td>
                    <div className="flex items-center justify-end gap-1">
                      <Button size="icon" variant="ghost" className="w-7 h-7" onClick={() => setPreviewDoc(doc)} title="Önizle" data-testid={`doc-eye-btn-${i}`}>
                        <Eye size={13} />
                      </Button>
                      <Button size="icon" variant="ghost" className="w-7 h-7" onClick={() => handleDownload(doc)} title="İndir" data-testid={`doc-download-btn-${i}`}>
                        <Download size={13} />
                      </Button>
                      <Button size="icon" variant="ghost" className="w-7 h-7 text-destructive hover:text-destructive" onClick={() => handleDelete(doc)} title="Arşivle" data-testid={`doc-delete-btn-${i}`}>
                        <Trash2 size={13} />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t text-xs text-muted-foreground">
            <span>{total} belgeden {Math.min((page - 1) * PAGE_SIZE + 1, total)}–{Math.min(page * PAGE_SIZE, total)} gösteriliyor</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Önceki</Button>
              <Button size="sm" variant="outline" disabled={page * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>Sonraki</Button>
            </div>
          </div>
        )}
      </div>

      {/* Upload Dialog */}
      <Dialog open={showUpload} onOpenChange={setShowUpload}>
        <DialogContent data-testid="upload-modal">
          <DialogHeader><DialogTitle className="gap-2 flex items-center"><Upload size={16} /> Belge Yükle</DialogTitle></DialogHeader>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="space-y-1.5">
              <Label>Dosya</Label>
              <div
                className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors"
                onClick={() => fileInputRef.current?.click()}
                data-testid="file-drop-zone"
              >
                {uploadForm.file ? (
                  <div className="flex items-center justify-center gap-2">
                    <FileIcon mimeType={uploadForm.file.type} />
                    <span className="text-sm font-medium">{uploadForm.file.name}</span>
                    <span className="text-xs text-muted-foreground">({formatBytes(uploadForm.file.size)})</span>
                  </div>
                ) : (
                  <div>
                    <Upload size={24} className="mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Dosya seç veya sürükle bırak</p>
                    <p className="text-xs text-muted-foreground mt-1">PDF, JPG, PNG, DOC, XLS, TXT — maks. 50MB</p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png,.gif,.webp,.doc,.docx,.xls,.xlsx,.txt,.csv"
                  onChange={e => setUploadForm(f => ({ ...f, file: e.target.files[0] || null }))}
                  data-testid="file-input"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>{t('documents.category')}</Label>
              <Select value={uploadForm.category || 'none'} onValueChange={v => setUploadForm(f => ({ ...f, category: v === 'none' ? '' : v }))}>
                <SelectTrigger data-testid="upload-category-select">
                  <SelectValue placeholder="Kategori seç (opsiyonel)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Kategori yok</SelectItem>
                  {CATEGORIES.map(c => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => { setShowUpload(false); setUploadForm({ category: '', file: null }); }}>Vazgeç</Button>
              <Button type="submit" disabled={uploading || !uploadForm.file} data-testid="upload-submit-btn">
                {uploading ? 'Yükleniyor...' : 'Yükle'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Preview Modal */}
      <PreviewModal doc={previewDoc} onClose={() => setPreviewDoc(null)} onDownload={handleDownload} />
    </div>
  );
}
