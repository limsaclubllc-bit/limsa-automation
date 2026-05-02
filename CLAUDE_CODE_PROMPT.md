# LIMSA CLUB — TAM OTOMASYON SİSTEMİ KURULUM TALİMATI
# Bu talimatı Claude Code'a ver, sistemi senin yerine kursun.

---

## SEN KİMSİN VE NE İSTİYORUM

Ben Ferhat. İki şirketim var:
- **Limsa Tekstil Sanayi Tic Ltd Şti** (Türkiye) — Trendyol satışları
- **Limsa Club LLC** (Florida, ABD) — Shopify + Etsy satışları

Nişantaşı'ndan tedarik ettiğim kadın giyim ürünleri (abiye, bluz, gece elbiseleri) satıyorum. Tek başıma yönetiyorum. Tüm satış kanallarını otomatik yöneten, 7/24 çalışan bir sistem istiyorum.

---

## MEVCUT PLATFORMLAR VE ERİŞİM

### Shopify
- URL: limsa.club
- MCP ile bağlı (Shopify MCP aktif)
- 10 aktif ürün, 18 sipariş var
- Basic plan, USD

### Trendyol  
- Supplier ID: 1124622
- API Key: UWm1olPStItZJU04UJdf
- API Secret: CebTGZas8KFrArlboTQn
- Entegrasyon Referans Kodu: 9002d266-ce1c-4d66-b83d-b27c38011abe
- Token: VVdtMW9sUFN0SXRaSlUwNFVKZGY6Q2ViVEdaYXM4S0ZyQXJsYm9UUW4=
- Aktif satış var, micro ihracat açıldı

### Etsy
- Henüz kurulmadı, Shopify ile aynı ürünler satılacak
- OAuth kurulumu yapılacak

### Stripe
- Account ID: acct_1Ruda31LGfgr0K97
- Live mode aktif

### Gmail
- info@limsa.club (raporlar buraya gelecek)

---

## İSTEDİĞİM SİSTEM

### 1. ÇALIŞMA MODELİ
- PC kapalı olsa bile 7/24 çalışsın
- Anthropic'in managed agent altyapısını kullan (sunucu kurmak istemiyorum)
- Türkçe komutlarla yönetilebilsin
- Telegram üzerinden de kontrol edebileyim

### 2. OTOMASYON GÖREVLERİ

**Sipariş Yönetimi:**
- Trendyol + Shopify + Etsy'deki tüm yeni siparişleri tek yerden gör
- Sipariş geldiğinde otomatik bildirim (Gmail + Telegram)
- Sipariş durumu takibi

**Stok Senkronizasyonu:**
- Bir platformda stok değişince diğerlerine otomatik yansısın
- Stok kritik seviyeye düşünce uyarı ver
- Mayıs/Haziran'da depo kurulacak, stok sistemine bağlanacak

**Ürün Yönetimi:**
- Shopify'daki ürünleri Trendyol ve Etsy'e otomatik aktar
- Fiyat güncellemesi yapılınca tüm platformlara yansısın
- Döviz kuru (USD/TRY) takibi ve otomatik fiyat hesaplama

**Finansal Takip:**
- Trendyol ödemelerini takip et
- Stripe ödemelerini takip et
- Haftalık kar/zarar raporu

**Raporlama:**
- Her sabah 08:00'de Gmail'e günlük özet
- Haftalık satış analizi
- Platform bazlı performans karşılaştırması

### 3. İLERİDE EKLENECEKLER
- Amazon USA
- Zalando (Almanya)
- Ozon (Rusya)
- Her platform bağımsız bağlantı ile (entegratör üzerinden değil)

---

## TEKNİK GEREKSİNİMLER

- Sunucu kurulumu istemiyorum (Anthropic altyapısı tercih)
- Eğer sunucu şartsa: Oracle Cloud Free Tier (ücretsiz)
- Ücretli 3. parti servis istemiyorum (Make.com, Zapier, n8n gibi)
- Python tercih
- Tüm credentials D:\Claude Limsa Club\_LIMSA_WORKSPACE\ klasöründe

---

## DOSYA KONUMLARI

Çalışma klasörü: D:\Claude Limsa Club\_LIMSA_WORKSPACE\
- MASTER_CONFIG.md — Tüm sistem bilgileri
- TRENDYOL_API.md — Trendyol API bilgileri
- ETSY_CONFIG.md — Etsy kurulum notları

---

## SENDEN İSTEDİKLERİM

1. Bu sistemi en uygun mimaride tasarla
2. Gerekli tüm kodları yaz
3. Kurulum adımlarını göster
4. 7/24 çalışması için ne gerektiğini söyle
5. Önce temel sistemi kur, sonra gelişmiş özellikleri ekle

Başla!
