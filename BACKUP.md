# Yedekleme Stratejisi — CateringSaaS

## Yedeklenecek Bileşenler

| Bileşen | Konum | Önem |
|---------|-------|------|
| MariaDB veritabanı | `catering_saas` DB | Kritik |
| Yüklenen belgeler | `/app/storage/` | Kritik |
| Ortam değişkenleri | `/app/backend/.env` | Yüksek |
| Uygulama kodu | `/app/` | Orta (git'te) |

---

## Veritabanı Yedeği

### Manuel Yedekleme

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/cateringsaas"
mkdir -p $BACKUP_DIR

# Tam dump
mysqldump -u saas_user -p'SaasSecure2024' catering_saas \
  --single-transaction \
  --routines \
  --triggers \
  > $BACKUP_DIR/db_$DATE.sql

# Sıkıştır
gzip $BACKUP_DIR/db_$DATE.sql

# 30 günden eski yedekleri sil
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Yedek tamamlandı: db_$DATE.sql.gz"
```

### Otomatik Günlük Yedek (cron)

```bash
# crontab -e ile ekleyin:
0 2 * * * /usr/local/bin/catering_backup.sh >> /var/log/catering_backup.log 2>&1
```

---

## Belge Depolama Yedeği

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/var/backups/cateringsaas"

# Depolanan belgeler
tar -czf $BACKUP_DIR/storage_$DATE.tar.gz /app/storage/

# 30 günden eski yedekleri sil
find $BACKUP_DIR -name "storage_*.tar.gz" -mtime +30 -delete
```

---

## Geri Yükleme

### Veritabanı Geri Yükleme

```bash
# 1. Mevcut veritabanını sil (dikkatli!)
mysql -u root -p -e "DROP DATABASE IF EXISTS catering_saas;"
mysql -u root -p -e "CREATE DATABASE catering_saas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. Yedeği geri yükle
gunzip -c /var/backups/cateringsaas/db_20260921_020000.sql.gz | \
  mysql -u saas_user -p'SaasSecure2024' catering_saas

# 3. Backend'i yeniden başlat
sudo supervisorctl restart backend
```

### Belge Depolama Geri Yükleme

```bash
tar -xzf /var/backups/cateringsaas/storage_20260921.tar.gz -C /
```

---

## Yedekleme Test Prosedürü

Her ay yapılması önerilen geri yükleme testi:

1. Test ortamına yedek DB yükle
2. Backend'i test ortamına yönelik başlat
3. `/api/health` endpoint'ini kontrol et
4. Login akışını test et
5. En az bir belgeyi listele ve indir

---

## Felaket Kurtarma (RPO/RTO)

| Senaryo | RPO (Veri Kaybı) | RTO (Kesinti Süresi) |
|---------|------------------|----------------------|
| Günlük yedekle | ≤ 24 saat | 2-4 saat |
| Saatlik yedekle | ≤ 1 saat | 1-2 saat |
| MariaDB Binary Log | ≈ 0 | 30-60 dakika |
