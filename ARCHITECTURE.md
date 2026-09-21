# Mimari Rehberi — CateringSaaS Phase 1

## 1. Genel Mimari Kararlar

### 1.1 Neden MySQL (MariaDB)?

Proje başlangıçta MongoDB ile planlanmış olsa da **kullanıcı talebi doğrultusunda MySQL 8+ / InnoDB** seçilmiştir:

- Muhasebe verileri için ACID uyumluluğu zorunludur
- Finansal kayıtlarda ilişkisel veri tutarlılığı kritiktir
- Kiracı izolasyonu `tenant_id` FK ile güçlü şekilde uygulanabilir
- Alembic ile yapısal migrasyon yönetimi

MariaDB, geliştirme ortamında MySQL 8+ uyumlu alternatif olarak kullanılmaktadır.

### 1.2 Multi-Tenant Stratejisi: Paylaşımlı Şema

Her tablo `tenant_id` sütunu içerir. Kiracı izolasyonu **tamamen backend katmanında** uygulanır:

```python
# core/deps.py — get_tenant_context
# X-Tenant-ID header'ından tenant alınır ve kullanıcının bu tenanta
# üye olup olmadığı doğrulanır. Her veri sorgusu tenant_id filtresi içerir.
```

**Avantajlar:** Basit yönetim, kolay ölçeklendirme
**Güvenlik:** Super admin bile başka kiracının verisine doğrudan erişemez

### 1.3 Auth: HTTP-only Cookie + Refresh Rotation

```
Kullanıcı → POST /api/auth/login
Backend  → access_token (15dk) + refresh_token (7gün) HTTP-only cookie set eder
Frontend → withCredentials:true ile tüm isteklere cookie eklenir
Süresi dolunca → POST /api/auth/refresh → yeni token çifti verilir
```

**Token Reuse Detection:** Bir refresh token kullanıldığında yeni hash ile güncellenir. Eski token tekrar kullanılırsa oturum iptal edilir.

---

## 2. Backend Katman Mimarisi

```
server.py (ASGI giriş noktası)
│
├── app/core/
│   ├── config.py     — Pydantic Settings, .env okuma
│   ├── database.py   — AsyncEngine, AsyncSession factory
│   ├── security.py   — Argon2id, JWT, TOTP, Fernet, Rate limiter
│   └── deps.py       — FastAPI bağımlılıkları (auth, tenant context)
│
├── app/models/       — SQLAlchemy ORM modelleri (Base + TimestampMixin)
│   ├── user.py       — User, TenantUser
│   ├── tenant.py     — Tenant, TenantSettings, TenantModule, Module
│   ├── role.py       — Role, Permission, RolePermission, UserRole
│   ├── auth.py       — UserSession, MFAConfig, RecoveryCode, LoginAttempt
│   ├── document.py   — Document
│   └── audit.py      — AuditLog
│
├── app/schemas/      — Pydantic v2 doğrulama şemaları
│   ├── auth.py
│   ├── user.py
│   ├── tenant.py
│   ├── role.py
│   └── document.py
│
├── app/api/          — FastAPI router'ları
│   ├── auth.py       — Giriş, MFA, oturum, şifre
│   ├── tenants.py    — Kiracı CRUD + modüller
│   ├── users.py      — Kullanıcı CRUD + rol atama
│   ├── roles.py      — Rol + yetki CRUD
│   ├── modules.py    — Modül toggle
│   ├── documents.py  — Belge yükleme/indirme
│   ├── audit_log.py  — Denetim kaydı listeleme
│   └── super_admin.py — Tüm kiracı yönetimi
│
└── app/services/
    ├── auth_service.py    — Oturum yönetimi, brute force
    ├── audit_service.py   — Audit log yazma helper
    └── storage_service.py — Dosya depolama soyutlaması
```

---

## 3. Frontend Katman Mimarisi

```
src/
├── App.js              — Router tanımları, ProtectedRoute
├── contexts/
│   ├── AuthContext.js  — Kullanıcı state, login/logout/verifyMFA
│   └── LanguageContext.js — i18n TR/EN
├── components/
│   ├── ProtectedRoute.js — Auth guard (requireSuperAdmin destekli)
│   └── layout/
│       ├── Layout.js     — Sidebar + Topbar wrapper
│       ├── Sidebar.js    — Navigasyon, collapsed mod
│       └── Topbar.js     — Kullanıcı menüsü, tenant switcher, dil
├── pages/
│   ├── Login.js
│   ├── MFAVerify.js
│   ├── MFASetup.js        — 3 adımlı QR → kod → recovery
│   ├── Dashboard.js
│   ├── Users.js
│   ├── Roles.js           — Yetki matrisi
│   ├── Modules.js
│   ├── TenantSettings.js  — Tab bazlı form
│   ├── Documents.js       — Yükleme, önizleme, filtre
│   ├── Security.js        — Oturum, şifre, MFA yönetimi
│   ├── AuditLog.js        — Filtrelenebilir, genişletilebilir tablo
│   └── super-admin/
│       ├── Tenants.js     — Kiracı yönetimi (Super Admin)
│       └── SystemHealth.js — Sistem metrikleri (Super Admin)
└── i18n/
    ├── tr.js    — Türkçe çeviriler
    └── en.js    — İngilizce çeviriler
```

---

## 4. Veritabanı Şeması

### Temel Tablolar

```sql
users          — id, email, password_hash, is_super_admin, mfa_enabled, status
tenant_users   — tenant_id, user_id, status, is_owner (N:N köprü)
tenants        — id, public_id, name, short_name, status
tenant_settings — tenant_id FK, ticari_unvan, vergi_no, para_birimi, ...
modules        — id, code, name_tr, name_en, is_core
tenant_modules — tenant_id, module_id, is_enabled (N:N köprü)
roles          — id, tenant_id, code, name, is_system_role
permissions    — id, code, name, module
role_permissions — role_id, permission_id (N:N)
user_roles     — user_id, role_id, tenant_id
documents      — tenant_id, public_id, original_filename, sha256_hash, mime_type, category, status
audit_logs     — tenant_id, user_id, action_type, severity, old_value, new_value, ip_address
user_sessions  — user_id, public_id, refresh_token_hash, is_revoked, last_used_at
mfa_configs    — user_id, totp_secret_encrypted, is_verified
recovery_codes — user_id, code_hash, is_used
login_attempts — identifier, ip_address, success, created_at
```

---

## 5. Güvenlik Kararları

| Alan | Karar | Sebep |
|------|-------|-------|
| Şifre | Argon2id | OWASP tavsiyesi, brute force dayanıklı |
| Token saklama | HTTP-only cookie | XSS'e karşı koruma (localStorage yerine) |
| TOTP şifreleme | Fernet (AES-128-CBC) | TOTP sırrı şifreli saklanır |
| Brute force | IP + email bazlı 15dk | Credential stuffing önleme |
| Rate limit | 10/dk login | SlowAPI middleware |
| Tenant izolasyonu | Backend enforced | Frontend'e güvenilmez |
| Soft delete | Belgeler arşivlenir | Muhasebe belgesi silinmez |
| Audit log | Tüm kritik işlemler | Yasal gereklillik |

---

## 6. Ölçeklenebilirlik Notları

- **Horizontal scaling:** Stateless backend, load balancer arkasında çalışabilir
- **Depolama:** `StorageService` soyutlaması S3 geçişini kolaylaştırır (`STORAGE_BACKEND=s3`)
- **Cache:** Redis ile oturum cache'i eklenebilir (hazır değil)
- **Migrasyon:** Alembic konfigürasyonu hazır, `alembic upgrade head` ile uygulanır
