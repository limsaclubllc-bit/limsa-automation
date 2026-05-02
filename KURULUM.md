# 🚀 LIMSA CLUB OTOMASYon SİSTEMİ — KURULUM KILAVUZU

> Tüm adımları sırayla uygula. ~2 saat içinde sistem 7/24 çalışmaya hazır olur.

---

## 📋 MİMARİ ÖZET

```
Sen (Telegram/Gmail)
    ↑↓
GitHub Actions (ücretsiz, 7/24, sunucu gerekmez)
    ├── Her 30 dakika → Sipariş kontrolü + Telegram komutları
    ├── Her 2 saat   → Stok senkronizasyonu
    ├── Her gün 08:00 → Günlük rapor (Gmail + Telegram)
    └── Her pazartesi → Haftalık analiz (Gmail)
         ↕
Trendyol API ←→ Shopify API ←→ Stripe API
```

**Neden GitHub Actions?**
- Ücretsiz (public repo → sınırsız dakika)
- Sunucu kurulumu YOK
- PC kapalı olsa bile çalışır
- Sıfır bakım

---

## ADIM 1: GITHUB REPOSU OLUŞTur

1. [github.com](https://github.com) → "New repository"
2. Repository adı: `limsa-automation` (veya istediğin ad)
3. **Public** seç (ücretsiz sınırsız dakika için)
4. "Create repository" tıkla

> ⚠️ Public repo olması credentials'ın görünmesi değil — API key'ler GitHub Secrets'ta saklanır, kodda yok.

### Kodu GitHub'a yükle:
```powershell
cd "D:\Claude Limsa Club\_LIMSA_WORKSPACE"
git init
git remote add origin https://github.com/KULLANICI_ADIN/limsa-automation.git
git add .
git commit -m "ilk kurulum"
git push -u origin main
```

---

## ADIM 2: SHOPIFY ADMIN API TOKEN AL

1. Shopify Admin → **Settings** → **Apps and sales channels**
2. **Develop apps** tıkla → **Create an app**
3. App adı: `Limsa Automation`
4. **Configure Admin API scopes** tıkla
5. Şu izinleri seç:
   - `read_orders`, `write_orders`
   - `read_products`, `write_products`
   - `read_inventory`, `write_inventory`
   - `read_fulfillments`
6. **Save** → **Install app** → **Reveal token once**
7. Token'ı kopyala → bir yere not et (bir daha göremezsin!)

---

## ADIM 3: TELEGRAM BOT OLUŞTur

1. Telegram'da **@BotFather**'a git
2. `/newbot` yaz
3. Bot adı: `Limsa Club Bot`
4. Kullanıcı adı: `limsaclub_bot` (benzersiz olmalı, `_bot` ile bitmeli)
5. Token'ı kopyala (şuna benzer: `123456789:ABC-DEF...`)

### Kendi Chat ID'ni öğren:
1. Yeni botu Telegram'da ara ve **START** gönder
2. Tarayıcıda aç: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. `"chat": {"id": 123456789}` — bu sayı senin Chat ID'n

---

## ADIM 4: GMAIL APP PASSWORD AL

1. [myaccount.google.com](https://myaccount.google.com) → **Security**
2. **2-Step Verification** → Etkinleştir (yoksa etkinleştir)
3. **App passwords** → **Other (custom name)** → `Limsa Bot`
4. 16 haneli şifreyi kopyala (boşluksuz yaz)

---

## ADIM 5: GITHUB SECRETS TANIMLA

GitHub repo sayfasında → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Her birini ayrı ayrı ekle:

| Secret Adı | Değer |
|------------|-------|
| `TRENDYOL_SUPPLIER_ID` | `1124622` |
| `TRENDYOL_API_KEY` | `UWm1olPStItZJU04UJdf` |
| `TRENDYOL_API_SECRET` | `CebTGZas8KFrArlboTQn` |
| `TRENDYOL_TOKEN` | `VVdtMW9sUFN0SXRaSlUwNFVKZGY6Q2ViVEdaYXM4S0ZyQXJsYm9UUW4=` |
| `SHOPIFY_STORE_URL` | `limsa.club` |
| `SHOPIFY_ACCESS_TOKEN` | *(Adım 2'den aldığın token)* |
| `STRIPE_SECRET_KEY` | *(Stripe Dashboard → API Keys → Secret key)* |
| `TELEGRAM_BOT_TOKEN` | *(Adım 3'ten)* |
| `TELEGRAM_CHAT_ID` | *(Adım 3'ten)* |
| `GMAIL_SENDER` | `info@limsa.club` |
| `GMAIL_APP_PASSWORD` | *(Adım 4'ten)* |
| `GMAIL_REPORT_RECIPIENT` | `info@limsa.club` |
| `CURRENCY_API_KEY` | *(opsiyonel — boş bırakabilirsin)* |

---

## ADIM 6: TRENDYOL SKU EŞLEŞMESİ TAMAMLA

`config/settings.json` dosyasında `trendyol_barcode` alanlarını doldur:

1. Trendyol Satıcı Paneli → Ürünler → Her ürünün barkodunu (SKU/barcode) bul
2. `settings.json` dosyasında ilgili ürünün `trendyol_barcode` alanına yaz
3. Değişikliği GitHub'a push et

---

## ADIM 7: SİSTEMİ TEST ET

### Yerel test (PC'de):
```powershell
cd "D:\Claude Limsa Club\_LIMSA_WORKSPACE"
python scheduler.py --task ping
```

Beklenen çıktı:
```
  ✅ OK — Trendyol
  ✅ OK — Shopify
  ✅ OK — Stripe
```

### GitHub Actions manuel tetikleme:
1. GitHub repo → **Actions** sekmesi
2. "Sipariş Kontrolü" workflow → **Run workflow** → **Run**
3. Çalışma loglarını kontrol et

---

## ADIM 8: TELEGRAM KOMUTLARINI TEST ET

Bot'a şu komutları gönder:
- `/start` — Yardım menüsü
- `/durum` — Sistem kontrolü
- `/siparisler` — Son siparişler
- `/stok` — Düşük stok
- `/gelir` — Finansal özet
- `/kur` — USD/TRY kuru
- `/rapor` — Anlık rapor

---

## 📅 OTOMATİK ÇALIŞMA TAKVİMİ

| Görev | Sıklık | Saat (TR) |
|-------|--------|-----------|
| Sipariş kontrolü | Her 30 dk | 06:00 – 23:00 |
| Stok senkronizasyonu | Her 2 saat | 06:00 – 23:00 |
| Telegram komutları | Her 30 dk | 06:00 – 23:00 |
| Günlük rapor (Gmail+Telegram) | Her gün | 08:00 |
| Haftalık analiz (Gmail) | Pazartesi | 08:00 |

---

## 🔮 SONRAKI ADIMLAR

### Etsy Entegrasyonu:
1. [etsy.com/developers](https://etsy.com/developers) → Yeni uygulama oluştur
2. OAuth 2.0 token al
3. `modules/etsy_api.py` oluştur (hazır şablon var)
4. `config/settings.json` → `etsy.enabled: true`

### Depo Kurulduğunda (Mayıs/Haziran):
- `stock_sync.py` → Depo sistemi API'sine bağla
- Merkezi envanter modülü ekle

### Gelecekte Eklenecek Platformlar:
- Amazon USA → `modules/amazon_api.py`
- Zalando → `modules/zalando_api.py`
- Ozon → `modules/ozon_api.py`

---

## ❓ SORUN GİDERME

**GitHub Actions çalışmıyor:**
- Actions sekmesinde "Enable Actions" gerekmiyorsa kontrol et
- Secrets doğru girildi mi?
- `git push` yapıldı mı?

**Trendyol bağlanamıyor:**
- Token'ın Base64 doğru mu? `echo -n "KEY:SECRET" | base64`
- IP kısıtlaması var mı? (Trendyol Paneli → API Ayarları)

**Telegram çalışmıyor:**
- Bot'a ilk mesajı kendin gönder (bot sana mesaj atamaz başlangıçta)
- Chat ID doğru mu?

**Gmail gönderimiyor:**
- App Password'de boşluk olmadığından emin ol
- 2FA aktif mi?

---

## 📊 MALİYET ÖZETI

| Servis | Maliyet |
|--------|---------|
| GitHub Actions | **Ücretsiz** (public repo) |
| GitHub repo | **Ücretsiz** |
| Telegram Bot | **Ücretsiz** |
| Gmail SMTP | **Ücretsiz** |
| Frankfurter (döviz) | **Ücretsiz** |
| **TOPLAM** | **$0/ay** |

---

*Sistem hazırlandı: 2026-05-02 | Limsa Club Otomasyon v1.0*
