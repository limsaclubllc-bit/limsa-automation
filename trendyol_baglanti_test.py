"""
LIMSA CLUB - Trendyol API Bağlantı Testi
Bu scripti çalıştır: python trendyol_baglanti_test.py
"""

import urllib.request
import urllib.error
import base64
import json

# ── Ayarlar ──────────────────────────────────────────
SUPPLIER_ID = "1124622"
API_KEY     = "Xw5oPVUNE4WghPLt6SFb"
API_SECRET  = "ZwEkhcTcBCq0japdPvfs"
BASE_URL    = "https://api.trendyol.com/sapigw"
# ─────────────────────────────────────────────────────

credentials = base64.b64encode(f"{API_KEY}:{API_SECRET}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {credentials}",
    "User-Agent": f"{SUPPLIER_ID} - SelfIntegration",
    "Content-Type": "application/json"
}

def api_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return {"hata": e.reason, "kod": e.code, "detay": e.read().decode()}, e.code
    except Exception as e:
        return {"hata": str(e)}, 0

def main():
    print("=" * 55)
    print("  LIMSA CLUB — Trendyol API Bağlantı Testi")
    print("=" * 55)

    # 1. Ürünleri çek
    print("\n📦 Ürünler kontrol ediliyor...")
    data, status = api_get(f"/suppliers/{SUPPLIER_ID}/products?page=0&size=10")
    if status == 200:
        toplam = data.get("totalElements", 0)
        print(f"✅ Bağlantı BAŞARILI! Toplam ürün: {toplam}")
        urunler = data.get("content", [])
        for u in urunler[:5]:
            print(f"   • {u.get('title','?')[:55]}  |  Stok: {u.get('quantity','?')}")
    else:
        print(f"❌ Ürün çekme hatası: {status} — {data}")

    # 2. Siparişleri çek
    print("\n🛒 Siparişler kontrol ediliyor...")
    data2, status2 = api_get(
        f"/suppliers/{SUPPLIER_ID}/orders?orderByField=PackageLastModifiedDate"
        f"&orderByDirection=DESC&page=0&size=5"
    )
    if status2 == 200:
        toplam2 = data2.get("totalElements", 0)
        print(f"✅ Toplam sipariş: {toplam2}")
        siparisler = data2.get("content", [])
        for s in siparisler[:3]:
            print(f"   • #{s.get('orderNumber','?')}  |  Durum: {s.get('status','?')}  |  Tutar: {s.get('grossAmount','?')} TL")
    else:
        print(f"❌ Sipariş çekme hatası: {status2} — {data2}")

    # 3. Mağaza bilgisi
    print("\n🏬 Mağaza bilgisi...")
    data3, status3 = api_get(f"/suppliers/{SUPPLIER_ID}/addresses")
    if status3 == 200:
        print(f"✅ Mağaza adresleri alındı")
    else:
        print(f"⚠️  Adres bilgisi: {status3}")

    print("\n" + "=" * 55)
    print("  Test tamamlandı. Sonuçları Claude'a kopyala.")
    print("=" * 55)

if __name__ == "__main__":
    main()
