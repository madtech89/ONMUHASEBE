# PRD — Catering / Küçük İşletme Ön Muhasebe SaaS

## Orijinal Problem Tanımı
Multi-tenant catering ve küçük işletme ön muhasebe SaaS platformu. Phase 1: Güvenli çok kiracılı çekirdek mimari.

**Teknoloji Stack:**
- Backend: FastAPI + SQLAlchemy (aiomysql) + MariaDB (MySQL 8+ uyumlu)
- Frontend: React + Tailwind CSS + Shadcn UI
- Auth: JWT (HTTP-only cookie) + Argon2id + TOTP MFA
- Mimari: Multi-tenant, Backend enforced isolation

## Kullanıcı Talepleri (Kesin Kısıtlar)
- Veritabanı: **MySQL 8+ / InnoDB** (MongoDB kesinlikle yok)
- Dil: **Türkçe** (UI + iletişim)
- Auth: **Kısa ömürlü access token**, refresh token rotation/reuse detection, **HTTP-only cookie**, MFA zorunlu
- **Phase 1 tamamlanmadan iş modülleri başlatılmaz**

## Kullanıcı Personaları
1. **Super Admin** — Tüm kiracıları yönetir, sistem sağlığını izler
2. **Tenant Admin (Firma Sahibi)** — Kendi firmasını yönetir, kullanıcı/rol ekler
3. **Tenant Kullanıcı** — Belirli yetkilerle işlem yapar

## Phase 1 — Core Architecture (TAMAMLANDI)

### Backend (100% Tamamlandı)
- [x] MariaDB kurulumu ve supervisor yönetimi
- [x] SQLAlchemy async modeller (users, tenants, roles, permissions, documents, audit, auth sessions)
- [x] Argon2id şifre hash + doğrulama
- [x] JWT (access: 15dk, refresh: 7 gün) HTTP-only cookie
- [x] Refresh token rotation + reuse detection
- [x] TOTP MFA (PyOTP + Fernet şifreleme)
- [x] 8 recovery code sistemi
- [x] Rate limiting (slowapi, 10/dk login)
- [x] Brute force koruması (15dk bekleme)
- [x] Multi-tenant backend izolasyonu (X-Tenant-ID header)
- [x] Granüler rol + yetki sistemi (26 izin, 7 rol)
- [x] Audit log (tüm kritik işlemler)
- [x] Belge yükleme (SHA-256, MIME doğrulama, 50MB limit, yerel depolama)
- [x] Super Admin API'leri
- [x] Seed: Super admin + Ecrin Yemek demo tenant

### Frontend (100% Tamamlandı)
- [x] Login sayfası
- [x] MFA doğrulama ve kurulum sayfaları
- [x] Dashboard (sistem durumu, audit özeti)
- [x] Kullanıcı Yönetimi (CRUD + rol atama)
- [x] Rol & Yetki Yönetimi (matris görünümü)
- [x] Modül Yönetimi (toggle)
- [x] Firma Ayarları (tab bazlı form)
- [x] Belge Merkezi (yükleme + listeleme + indirme + önizleme + kategori filtresi)
- [x] Güvenlik & MFA (oturum yönetimi + şifre değiştirme)
- [x] Denetim Kaydı (filtreli, genişletilebilir satırlar)
- [x] Super Admin — Kiracı Yönetimi
- [x] Super Admin — Sistem Sağlığı
- [x] i18n TR/EN

## Phase 1 Tamamlandı — KİLİTLENDİ (PHASE_1_LOCKED_READY_FOR_PHASE_2)

### Final QA Test Sonuçları ✅
- test_api.py: **17/17 PASS**
- test_phase1_final_qa.py: **36/36 PASS** (3 skip: test ortamı IP hız sınırı)
- Güvenlik: tenant izolasyonu, JWT cookies, MFA, permissions hepsi PASS
- Tüm 10 frontend sayfası hatasız yükleniyor

### QA'da Düzeltilen Hatalar ✅
1. AssignRoleRequest şeması: gereksiz user_public_id kaldırıldı
2. super_admin.py, tenants.py, roles.py, deps.py: SQLAlchemy async lazy-loading (selectinload) düzeltildi
3. /settings/tenant sayfası 500 hatası: tenant.settings lazy-load sorunu giderildi

### Dokümantasyon (Türkçe) ✅
- [x] README.md — kurulum ve kullanım
- [x] ARCHITECTURE.md — mimari kararlar, bileşenler
- [x] PROJECT_STATE.md — Phase 1 final QA raporu
- [x] PORTABILITY.md — taşıma kılavuzu
- [x] BACKUP.md — yedekleme stratejileri
- [x] .env.example — tüm değişkenler

## Phase 2 — İş Modülleri (DONDURULMUŞ)
Kullanıcı tarafından Phase 1 tamamen bitmeden başlatılmaması talep edilmiştir.

- [ ] Catering / Sipariş Yönetimi
- [ ] Cari Hesaplar
- [ ] Fatura & İrsaliye
- [ ] Kasa & Banka
- [ ] Stok Yönetimi
- [ ] Personel & Bordro
- [ ] Mali Müşavir Merkezi
- [ ] Raporlar

## Kritik Bilgiler
- **Preview URL**: https://kitchen-admin-suite.preview.emergentagent.com
- **Backend**: FastAPI, port 8001 (supervisor)
- **Frontend**: React, port 3000 (supervisor)
- **DB**: MariaDB (`catering_saas` veritabanı, `saas_user`)
- **Super Admin**: furkanafsin73@gmail.com / JlMykl5STjjeH_eXxjZkCQ
- **Demo Tenant**: Ecrin Yemek

## Dosya Yapısı
```
/app
├── backend/
│   ├── app/
│   │   ├── api/ (auth, tenants, users, roles, modules, documents, audit_log, super_admin)
│   │   ├── core/ (config, database, security, deps)
│   │   ├── models/ (auth, audit, base, document, role, tenant, user)
│   │   ├── schemas/ (auth, document, role, tenant, user)
│   │   └── services/ (audit_service, auth_service, storage_service)
│   ├── seeds.py
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/ (ProtectedRoute, layout/, ui/)
│   │   ├── contexts/ (AuthContext, LanguageContext)
│   │   ├── i18n/ (tr.js, en.js)
│   │   └── pages/ (Login, MFA*, Dashboard, Users, Roles, Modules,
│   │              TenantSettings, Documents, Security, AuditLog,
│   │              super-admin/Tenants, super-admin/SystemHealth)
├── memory/
│   ├── PRD.md (bu dosya)
│   └── test_credentials.md
```

## Değişiklik Günlüğü
- **2026-09-21**: Phase 1 tüm frontend sayfaları tamamlandı (Documents, Security, AuditLog, Super Admin sayfaları)
- **2026-09-21**: Backend API, auth, MFA, seed tamamlandı
- **2026-09-21**: MariaDB kurulumu ve supervisor konfigürasyonu
