# Taşınabilirlik Rehberi — CateringSaaS

Bu belge, uygulamayı farklı ortamlara (VPS, Docker, bulut) taşımak için gereken adımları açıklar.

---

## Ortam Değişkenleri

Tüm hassas değerler `.env` dosyasında tutulur. `.env.example` dosyasını referans alın.

### Backend `.env` Değişkenleri

| Değişken | Açıklama | Örnek |
|----------|----------|-------|
| `ASYNC_DATABASE_URL` | Async MySQL bağlantısı | `mysql+aiomysql://user:pass@host/db` |
| `SYNC_DATABASE_URL` | Sync MySQL bağlantısı (seed) | `mysql+pymysql://user:pass@host/db` |
| `JWT_SECRET` | JWT imzalama anahtarı (min 32 byte) | Rastgele üret |
| `JWT_ALGORITHM` | HS256 | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token ömrü | 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token ömrü | 7 |
| `TOTP_ENCRYPTION_KEY` | Fernet anahtarı (TOTP şifreleme) | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `COOKIE_SECURE` | HTTPS için true | false (dev), true (prod) |
| `STORAGE_BACKEND` | `local` veya `s3` | local |
| `STORAGE_LOCAL_PATH` | Yerel depolama dizini | /app/storage |
| `SUPER_ADMIN_EMAIL` | İlk super admin e-posta | admin@example.com |
| `SUPER_ADMIN_PASSWORD` | İlk super admin şifre | Güçlü şifre |

### Frontend `.env` Değişkenleri

| Değişken | Açıklama |
|----------|----------|
| `REACT_APP_BACKEND_URL` | Backend dış URL (nginx proxy'li) |

---

## Yerel Ortamdan Yeni Ortama Geçiş

### 1. Veritabanı

```bash
# Kaynak ortamda dump alın
mysqldump -u saas_user -p catering_saas > backup_$(date +%Y%m%d).sql

# Hedef ortamda oluşturun
mysql -u root -p -e "CREATE DATABASE catering_saas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER 'saas_user'@'%' IDENTIFIED BY 'YeniSifre';"
mysql -u root -p -e "GRANT ALL ON catering_saas.* TO 'saas_user'@'%';"
mysql -u saas_user -p catering_saas < backup_*.sql
```

### 2. Depolanan Belgeler

```bash
# /app/storage dizinini kopyalayın
rsync -avz /app/storage/ hedef_sunucu:/app/storage/
```

### 3. Çevre Değişkenleri

```bash
# .env.example dosyasını kopyalayın ve değerleri doldurun
cp .env.example /app/backend/.env
# JWT_SECRET ve TOTP_ENCRYPTION_KEY yeni ortam için üretin
```

---

## Docker ile Çalıştırma (Opsiyonel)

```dockerfile
# Örnek docker-compose yapısı
services:
  db:
    image: mariadb:10.11
    environment:
      MYSQL_ROOT_PASSWORD: root_pass
      MYSQL_DATABASE: catering_saas
      MYSQL_USER: saas_user
      MYSQL_PASSWORD: saas_pass

  backend:
    build: ./backend
    env_file: ./backend/.env
    depends_on: [db]
    ports: ["8001:8001"]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
```

---

## Production Kontrol Listesi

- [ ] `COOKIE_SECURE=true` (HTTPS zorunlu)
- [ ] `DEBUG=false`
- [ ] Güçlü `JWT_SECRET` (openssl rand -hex 64)
- [ ] Yeni `TOTP_ENCRYPTION_KEY` üretildi
- [ ] `SUPER_ADMIN_PASSWORD` değiştirildi
- [ ] Nginx/Caddy ile HTTPS yapılandırıldı
- [ ] MariaDB erişimi sadece localhost ile kısıtlandı
- [ ] `/app/storage` için düzenli yedekleme ayarlandı
- [ ] Rate limit değerleri production için ayarlandı
