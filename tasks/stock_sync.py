"""
Stok Senkronizasyonu — Shopify stoklarını Trendyol ile karşılaştırır,
kritik seviyelerde uyarı gönderir.
Tam çift yönlü sync: Shopify master kaynak, Trendyol güncellenir.
"""

from modules.trendyol_api  import TrendyolAPI
from modules.shopify_api   import ShopifyAPI
from modules.telegram_bot  import send_low_stock_alert, send_error_alert
from modules import state_manager as sm
from modules.config_loader  import get_settings
from modules.logger         import get_logger

log = get_logger("stock_sync")


def _get_shopify_inventory(api: ShopifyAPI) -> dict:
    """SKU → {variant_id, inventory_item_id, title, quantity} eşlemesi döndür."""
    products   = api.get_products()
    locations  = api.get_locations()
    location_id = locations[0]["id"] if locations else None

    inventory = {}
    for p in products:
        p_title = p.get("title", "")
        for v in p.get("variants", []):
            sku = v.get("sku", "").strip()
            if not sku:
                continue
            inventory[sku] = {
                "variant_id":        v["id"],
                "inventory_item_id": v.get("inventory_item_id"),
                "product_title":     p_title,
                "variant_title":     v.get("title", ""),
                "quantity":          v.get("inventory_quantity", 0),
                "price":             float(v.get("price", 0)),
                "location_id":       location_id,
            }
    log.info("Shopify envanter: %d SKU yüklendi", len(inventory))
    return inventory


def _get_trendyol_inventory(api: TrendyolAPI) -> dict:
    """Barcode → {title, quantity, salePrice} eşlemesi döndür."""
    products  = api.get_all_products()
    inventory = {}
    for p in products:
        barcode = p.get("barcode", "").strip()
        if barcode:
            inventory[barcode] = {
                "title":      p.get("title", ""),
                "quantity":   p.get("quantity", 0),
                "sale_price": p.get("salePrice", 0),
                "list_price": p.get("listPrice", 0),
            }
    log.info("Trendyol envanter: %d ürün yüklendi", len(inventory))
    return inventory


def check_low_stock(shopify_inventory: dict, settings: dict) -> list:
    low_threshold      = settings["inventory"]["low_stock_threshold"]
    critical_threshold = settings["inventory"]["critical_stock_threshold"]
    alerts = []

    for sku, item in shopify_inventory.items():
        qty = item["quantity"]
        if qty <= low_threshold:
            level   = "KRİTİK" if qty <= critical_threshold else "DÜŞÜK"
            product = item["product_title"]
            variant = item["variant_title"]
            log.warning("Düşük stok: %s %s — %d adet [%s]", product, variant, qty, level)

            send_low_stock_alert(
                product_name=product,
                variant=variant,
                quantity=qty,
                platform="Shopify",
            )
            alerts.append({
                "product":  product,
                "variant":  variant,
                "quantity": qty,
                "sku":      sku,
                "level":    level,
            })
    return alerts


def sync_trendyol_from_shopify(shopify_inv: dict, trendyol_inv: dict,
                                api: TrendyolAPI, settings: dict) -> int:
    """Shopify stok değişikliklerini Trendyol'a yansıt (SKU=barcode eşleşmesi)."""
    if not settings["inventory"]["sync_enabled"]:
        log.info("Stok sync devre dışı (settings.json)")
        return 0

    updates = []
    for sku, shopify_item in shopify_inv.items():
        if sku not in trendyol_inv:
            continue
        ty_item  = trendyol_inv[sku]
        sh_qty   = shopify_item["quantity"]
        ty_qty   = ty_item["quantity"]

        if sh_qty != ty_qty:
            log.info("Stok farkı — SKU %s: Shopify=%d, Trendyol=%d → güncelleniyor",
                     sku, sh_qty, ty_qty)
            updates.append({
                "barcode":   sku,
                "quantity":  sh_qty,
                "salePrice": ty_item["sale_price"],
                "listPrice": ty_item["list_price"],
            })

    BATCH_SIZE = 50  # Trendyol API limiti
    if updates:
        try:
            for i in range(0, len(updates), BATCH_SIZE):
                batch = updates[i:i + BATCH_SIZE]
                api.update_price_and_stock(batch)
                log.info("Trendyol %d stok güncellendi (batch %d)", len(batch), i // BATCH_SIZE + 1)
        except Exception as e:
            log.error("Trendyol stok güncelleme hatası: %s", e)
            send_error_alert("StokSync→Trendyol", str(e))

    return len(updates)


def run(state: dict = None, snapshot: dict = None) -> dict:
    if state is None:
        state, snapshot = sm.load()

    settings = get_settings()
    log.info("Stok sync başlıyor...")

    try:
        sh_api = ShopifyAPI()
        ty_api = TrendyolAPI()

        shopify_inv   = _get_shopify_inventory(sh_api)
        trendyol_inv  = _get_trendyol_inventory(ty_api)

        alerts        = check_low_stock(shopify_inv, settings)
        updated_count = sync_trendyol_from_shopify(
            shopify_inv, trendyol_inv, ty_api, settings)

        sm.mark_run("stock_sync", state)
        sm.save(state, snapshot)

        result = {
            "shopify_skus":   len(shopify_inv),
            "trendyol_skus":  len(trendyol_inv),
            "low_stock_alerts": alerts,
            "trendyol_updated": updated_count,
        }
        log.info("Stok sync tamamlandı: %s", result)
        return result

    except Exception as e:
        log.error("Stok sync genel hata: %s", e)
        send_error_alert("StokSync", str(e))
        return {"error": str(e)}


if __name__ == "__main__":
    r = run()
    print(f"\nShopify SKU: {r.get('shopify_skus')}")
    print(f"Trendyol SKU: {r.get('trendyol_skus')}")
    print(f"Düşük stok: {len(r.get('low_stock_alerts', []))}")
    print(f"Trendyol güncellendi: {r.get('trendyol_updated')}")
