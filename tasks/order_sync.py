"""
Sipariş Senkronizasyonu — Trendyol ve Shopify'dan yeni siparişleri çeker,
Telegram + Gmail bildirimi gönderir, state'i günceller.
"""

from datetime import datetime, timedelta
from modules.trendyol_api  import TrendyolAPI
from modules.shopify_api   import ShopifyAPI
from modules.telegram_bot  import send_order_alert, send_error_alert
from modules.gmail_reporter import send_email
from modules import state_manager as sm
from modules.logger import get_logger

log = get_logger("order_sync")


def _format_trendyol_order(o: dict) -> dict:
    lines = o.get("lines", [])
    items = "; ".join(f"{l.get('productName','?')} x{l.get('quantity',1)}"
                      for l in lines)
    return {
        "platform":  "Trendyol",
        "order_id":  str(o.get("orderNumber", "")),
        "customer":  o.get("shipmentAddress", {}).get("fullName", "—"),
        "amount":    str(round(o.get("grossAmount", 0), 2)),
        "currency":  "TRY",
        "status":    o.get("status", ""),
        "items":     items,
        "date":      datetime.fromtimestamp(
                         o.get("orderDate", 0) / 1000
                     ).strftime("%d.%m.%Y %H:%M") if o.get("orderDate") else "—",
    }


def _format_shopify_order(o: dict) -> dict:
    items = "; ".join(
        f"{li.get('name','?')} x{li.get('quantity',1)}"
        for li in o.get("line_items", [])
    )
    customer = o.get("shipping_address", {}) or o.get("billing_address", {}) or {}
    name = f"{customer.get('first_name','')} {customer.get('last_name','')}".strip()
    if not name:
        c = o.get("customer", {}) or {}
        name = f"{c.get('first_name','')} {c.get('last_name','')}".strip() or "—"
    return {
        "platform":  "Shopify",
        "order_id":  o.get("name", str(o.get("id",""))),
        "customer":  name,
        "amount":    o.get("total_price", "0"),
        "currency":  o.get("currency", "USD"),
        "status":    o.get("financial_status", ""),
        "items":     items,
        "date":      o.get("created_at", "")[:16].replace("T", " "),
    }


def _notify_orders_batch(orders: list) -> None:
    """Birden fazla sipariş varsa tek mesajda gönder; tekse doğrudan alert."""
    if not orders:
        return
    if len(orders) == 1:
        o = orders[0]
        send_order_alert(platform=o["platform"], order_id=o["order_id"],
                         customer=o["customer"], amount=o["amount"], currency=o["currency"])
        return
    lines = [f"🛍 <b>{len(orders)} YENİ SİPARİŞ</b>\n"]
    for o in orders:
        lines.append(f"[{o['platform']}] #{o['order_id']} — {o['customer']} — "
                     f"{o['amount']} {o['currency']}")
    from modules.telegram_bot import send
    send("\n".join(lines))
    log.info("Toplu bildirim gönderildi: %d sipariş", len(orders))


def run_trendyol(state: dict) -> dict:
    """Trendyol'dan yeni siparişleri çek ve bildir."""
    log.info("Trendyol sipariş kontrolü başlıyor...")
    api        = TrendyolAPI()
    last_ts    = state.get("last_trendyol_order_ts", 0)
    new_orders = []

    try:
        data    = api.get_orders(page=0, size=50)
        orders  = data.get("content", [])
        for o in orders:
            order_ts = o.get("orderDate", 0)
            if order_ts > last_ts:
                new_orders.append(_format_trendyol_order(o))
                last_ts = max(last_ts, order_ts)

        _notify_orders_batch(new_orders)
        log.info("Trendyol: %d yeni sipariş", len(new_orders))

        state["last_trendyol_order_ts"] = last_ts
        state["stats"]["total_trendyol_orders"] = state["stats"].get(
            "total_trendyol_orders", 0) + len(new_orders)

    except Exception as e:
        log.error("Trendyol sipariş hatası: %s", e)
        send_error_alert("Trendyol SiparişSync", str(e))

    return {"new_orders": new_orders, "state": state}


def run_shopify(state: dict) -> dict:
    """Shopify'dan yeni siparişleri çek ve bildir."""
    log.info("Shopify sipariş kontrolü başlıyor...")
    api       = ShopifyAPI()
    last_id   = state.get("last_shopify_order_id", 0)
    new_orders = []

    try:
        orders = api.get_orders(status="any", limit=50,
                                since_id=last_id if last_id else None)
        for o in orders:
            oid = int(o.get("id", 0))
            new_orders.append(_format_shopify_order(o))
            last_id = max(last_id, oid)

        _notify_orders_batch(new_orders)
        log.info("Shopify: %d yeni sipariş", len(new_orders))

        state["last_shopify_order_id"] = last_id
        state["stats"]["total_shopify_orders"] = state["stats"].get(
            "total_shopify_orders", 0) + len(new_orders)

    except Exception as e:
        log.error("Shopify sipariş hatası: %s", e)
        send_error_alert("Shopify SiparişSync", str(e))

    return {"new_orders": new_orders, "state": state}


def run(state: dict = None, snapshot: dict = None) -> dict:
    """Tüm platformları kontrol et."""
    if state is None:
        state, snapshot = sm.load()

    all_new = []

    result_ty = run_trendyol(state)
    state     = result_ty["state"]
    all_new  += result_ty["new_orders"]

    result_sh = run_shopify(state)
    state     = result_sh["state"]
    all_new  += result_sh["new_orders"]

    sm.mark_run("order_sync", state)
    sm.save(state, snapshot)

    log.info("Sipariş sync tamamlandı — toplam %d yeni sipariş", len(all_new))
    return {"new_orders": all_new, "state": state}


if __name__ == "__main__":
    result = run()
    print(f"\nYeni sipariş sayısı: {len(result['new_orders'])}")
    for o in result["new_orders"]:
        print(f"  [{o['platform']}] #{o['order_id']} — {o['customer']} — "
              f"{o['amount']} {o['currency']}")
