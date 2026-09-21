# CateringSaaS — Catering & Küçük İşletme Ön Muhasebe SaaS

## Genel Bakış

CateringSaaS, catering işletmeleri ve küçük işletmeler için geliştirilmiş **çok kiracılı (multi-tenant)** bir ön muhasebe SaaS platformudur. Bu platform; fatura, irsaliye, cari hesaplar, stok, sipariş ve belge yönetimini tek çatı altında toplamak üzere tasarlanmıştır.

**Mevcut Durum:** Phase 1 — Core Architecture (Tamamlandı)

---

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Backend | FastAPI (Python 3.11+) + SQLAlchemy async (aiomysql) |
| Veritabanı | MariaDB 10.x (MySQL 8+ uyumlu, InnoDB) |
| Frontend | React 18 + Tailwind CSS + Shadcn UI |
| Auth | JWT (HTTP-only cookie) + Argon2id + TOTP MFA (PyOTP) |
| Depolama | Yerel dosya sistemi (S3-uyumlu soyutlama katmanı) |
| Process | Supervisor (backend + frontend + MariaDB) |

---

## Hızlı Başlangıç

### Gereksinimler

- Python 3.11+
- Node.js 18+ (yarn)
- MariaDB 10.x veya MySQL 8+

### 1. Backend Kurulumu

```bash
cd /app/backend
pip install -r requirements.txt

# .env dosyasını oluşturun (.env.example'dan kopyalayın)
cp ../.env.example .env
# .env içindeki değerleri doldurun

# Veritabanını başlatın (MariaDB çalışıyor olmalı)
python seeds.py
```

### 2. Frontend Kurulumu

```bash
cd /app/frontend
yarn install

# .env dosyasını oluşturun
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env
```

### 3. Servisleri Başlatma

```bash
# Backend
cd /app/backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd /app/frontend
yarn start
```

---

## Varsayılan Hesaplar (Geliştirme)

| Rol | E-posta | Şifre |
|-----|---------|-------|
| Super Admin | furkanafsin73@gmail.com | JlMykl5STjjeH_eXxjZkCQ |

**Demo Kiracı:** Ecrin Yemek (Ecrin Yemek Catering)

---

## API Dokümantasyonu

Uygulama çalışırken Swagger UI'ye erişin:

```
http://localhost:8001/api/docs
```

### Temel Endpoint'ler

```
POST   /api/auth/login          — Giriş
GET    /api/auth/me             — Mevcut kullanıcı
POST   /api/auth/refresh        — Token yenile
POST   /api/auth/logout         — Çıkış
POST   /api/auth/mfa/setup      — MFA kurulumu başlat
POST   /api/auth/mfa/enable     — MFA etkinleştir
POST   /api/auth/mfa/verify     — MFA doğrula (giriş sırasında)
POST   /api/auth/change-password — Şifre değiştir

GET    /api/tenants/my          — Kendi kiracılarım
GET    /api/users/              — Kullanıcı listesi (kiracı)
GET    /api/roles/              — Rol listesi (kiracı)
GET    /api/documents/          — Belge listesi
POST   /api/documents/upload    — Belge yükle
GET    /api/audit/              — Denetim kaydı

GET    /api/super-admin/tenants        — Tüm kiracılar
POST   /api/super-admin/tenants        — Yeni kiracı
GET    /api/super-admin/system/health  — Sistem sağlığı
```

---

## Proje Yapısı

```
/app
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI router'ları
│   │   ├── core/           # Config, DB, Güvenlik, Deps
│   │   ├── models/         # SQLAlchemy ORM modelleri
│   │   ├── schemas/        # Pydantic şemaları
│   │   └── services/       # İş mantığı servisleri
│   ├── alembic/            # Veritabanı migrasyonları
│   ├── seeds.py            # Başlangıç verisi
│   ├── server.py           # ASGI giriş noktası
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/     # Yeniden kullanılabilir bileşenler
│       ├── contexts/       # React context'leri (Auth, Dil)
│       ├── i18n/           # Çeviri dosyaları (TR, EN)
│       └── pages/          # Sayfa bileşenleri
├── memory/
│   ├── PRD.md
│   └── test_credentials.md
├── ARCHITECTURE.md
├── PROJECT_STATE.md
├── PORTABILITY.md
├── BACKUP.md
├── .env.example
└── storage/               # Yüklenen belgeler (yerel)
```

---

## Güvenlik Mimarisi

- **Kimlik Doğrulama:** JWT token çifti (access + refresh) HTTP-only cookie olarak saklanır
- **Şifre Hashing:** Argon2id (password-argon2 kütüphanesi)
- **MFA:** TOTP (RFC 6238), Fernet şifreli gizli anahtar, 8 kurtarma kodu
- **Token Güvenliği:** Refresh token rotation + reuse detection, 15 dakika kısa ömürlü access token
- **Brute Force:** IP + e-posta bazlı 15 dakika bekleme süresi
- **Rate Limiting:** SlowAPI ile 10 istek/dakika (login endpoint)
- **Tenant İzolasyonu:** Backend katmanında X-Tenant-ID header doğrulaması

---

## Lisans

Özel proje — Tüm hakları saklıdır.
