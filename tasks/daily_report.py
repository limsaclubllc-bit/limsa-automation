"""
Günlük ve haftalık rapor üretici.
Her gün 08:00'de çalışır; pazartesi ek olarak haftalık analiz gönderir.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from modules.shopify_api    import ShopifyAPI
from modules.trendyol_api   import TrendyolAPI
from modules.stripe_api     import StripeAPI
from modules.gmail_reporter import send_daily_report, send_weekly_report
from modules.telegram_bot   import send_daily_summary
from modules import state_manager as sm
from modules.config_loader  import TZ_ISTANBUL, LOW_STOCK_THRESHOLD
from modules.logger import get_logger

log = get_logger("daily_report")


def _shopify_stats(api: ShopifyAPI) -> dict:
    try:
        now       = datetime.now(TZ_ISTANBUL)
        today_min = now.replace(hour=0, minute=0, second=0).isoformat()
        month_min = now.replace(day=1, hour=0, minute=0, second=0).isoformat()

        all_orders    = api.get_orders(status="any", limit=250,
                                       created_at_min=month_min)
        today_orders  = [o for o in all_orders
                         if o.get("created_at", "") >= today_min]

        today_revenue  = sum(float(o.get("total_price", 0)) for o in today_orders)
        month_revenue  = sum(float(o.get("total_price", 0)) for o in all_orders)
        products       = api.get_products()

        return {
            "today_orders":   len(today_orders),
            "today_revenue":  round(today_revenue, 2),
            "month_orders":   len(all_orders),
            "month_revenue":  round(month_revenue, 2),
            "active_products": len(products),
        }
    except Exception as e:
        log.error("Shopify stats hatası: %s", e)
        return {}


def _trendyol_stats(api: TrendyolAPI) -> dict:
    try:
        data    = api.get_orders(page=0, size=200)
        orders  = data.get("content", [])

        now_ts  = datetime.now(TZ_ISTANBUL).timestamp() * 1000
        day_ms  = 24 * 3600 * 1000
        new     = [o for o in orders if o.get("orderDate", 0) > now_ts - day_ms]
        pending = [o for o in orders if o.get("status") in ("Created", "Picking")]

        return {
            "new_orders":     len(new),
            "pending_orders": len(pending),
            "pending_payment": "—",
        }
    except Exception as e:
        log.error("Trendyol stats hatası: %s", e)
        return {}


def _stripe_stats(api: StripeAPI) -> dict:
    try:
        balance = api.get_balance()
        weekly  = api.get_weekly_revenue()
        return {
            "balance_usd":  balance["available"].get("USD", 0),
            "week_revenue": weekly["total_usd"],
            "week_orders":  weekly["order_count"],
        }
    except Exception as e:
        log.error("Stripe stats hatası: %s", e)
        return {}


def _stock_alerts(api: ShopifyAPI) -> list:
    alerts = []
    try:
        for p in api.get_products():
            for v in p.get("variants", []):
                qty = v.get("inventory_quantity", 0) or 0
                if qty <= LOW_STOCK_THRESHOLD:
                    alerts.append({
                        "product":  p.get("title", ""),
                        "variant":  v.get("title", ""),
                        "quantity": qty,
                    })
    except Exception as e:
        log.error("Stok alert hatası: %s", e)
    return alerts


def build_telegram_summary(shopify: dict, trendyol: dict, stripe: dict,
                            low_stock: list) -> str:
    lines = [
        f"📅 {datetime.now(TZ_ISTANBUL).strftime('%d.%m.%Y %H:%M')}",
        "",
        f"🛍 <b>Shopify</b>",
        f"  Bugün: {shopify.get('today_orders',0)} sipariş / ${shopify.get('today_revenue',0):.2f}",
        f"  Bu ay: {shopify.get('month_orders',0)} sipariş / ${shopify.get('month_revenue',0):.2f}",
        "",
        f"🛒 <b>Trendyol</b>",
        f"  Yeni (24s): {trendyol.get('new_orders',0)} sipariş",
        f"  Bekleyen: {trendyol.get('pending_orders',0)} adet",
        "",
        f"💳 <b>Stripe</b>",
        f"  Bakiye: ${stripe.get('balance_usd',0):.2f}",
        f"  Bu hafta: ${stripe.get('week_revenue',0):.2f}",
    ]
    if low_stock:
        lines += ["", "⚠️ <b>Kritik Stok:</b>"]
        for s in low_stock[:5]:
            lines.append(f"  • {s['product']} {s['variant']}: {s['quantity']} adet")
    return "\n".join(lines)


def run_daily(state: dict = None, snapshot: dict = None) -> bool:
    if state is None:
        state, snapshot = sm.load()

    log.info("Günlük rapor hazırlanıyor...")

    sh_api = ShopifyAPI()
    ty_api = TrendyolAPI()
    st_api = StripeAPI()

    # Üç platform istatistiği + stok kontrolü paralel çalışır (~3x hızlı)
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_shopify  = pool.submit(_shopify_stats, sh_api)
        f_trendyol = pool.submit(_trendyol_stats, ty_api)
        f_stripe   = pool.submit(_stripe_stats, st_api)
        f_alerts   = pool.submit(_stock_alerts, sh_api)

    shopify  = f_shopify.result()
    trendyol = f_trendyol.result()
    stripe   = f_stripe.result()
    alerts   = f_alerts.result()

    report_data = {
        "shopify":   shopify,
        "trendyol":  trendyol,
        "stripe":    stripe,
        "low_stock": alerts,
        "alerts":    [],
    }

    # Telegram özeti
    tg_summary = build_telegram_summary(shopify, trendyol, stripe, alerts)
    send_daily_summary(tg_summary)

    # Gmail raporu
    ok = send_daily_report(report_data)

    sm.mark_run("daily_report", state)
    sm.save(state, snapshot)

    log.info("Günlük rapor gönderildi: %s", "OK" if ok else "HATA")
    return ok


def run_weekly(state: dict = None, snapshot: dict = None) -> bool:
    if state is None:
        state, snapshot = sm.load()

    log.info("Haftalık rapor hazırlanıyor...")

    sh_api = ShopifyAPI()
    st_api = StripeAPI()

    now        = datetime.now(TZ_ISTANBUL)
    week_start = now - timedelta(days=7)
    week_min   = week_start.replace(hour=0, minute=0, second=0).isoformat()

    try:
        orders    = sh_api.get_orders(status="any", limit=250,
                                      created_at_min=week_min)
        sh_rev    = sum(float(o.get("total_price", 0)) for o in orders)
        weekly_st = st_api.get_weekly_revenue()

        report_data = {
            "from_date":     week_start.strftime("%d.%m.%Y"),
            "to_date":       now.strftime("%d.%m.%Y"),
            "total_revenue": round(sh_rev + weekly_st["total_usd"], 2),
            "total_orders":  len(orders) + weekly_st["order_count"],
            "platforms": {
                "Shopify": {
                    "orders":    len(orders),
                    "revenue":   round(sh_rev, 2),
                    "avg_order": round(sh_rev / len(orders), 2) if orders else 0,
                },
                "Stripe": {
                    "orders":    weekly_st["order_count"],
                    "revenue":   weekly_st["total_usd"],
                    "avg_order": weekly_st["avg_order_usd"],
                },
            },
        }
        ok = send_weekly_report(report_data)
        sm.mark_run("weekly_report", state)
        sm.save(state, snapshot)
        return ok

    except Exception as e:
        log.error("Haftalık rapor hatası: %s", e)
        return False


def run(state: dict = None, snapshot: dict = None) -> bool:
    if state is None:
        state, snapshot = sm.load()

    daily_ok = run_daily(state, snapshot)

    if datetime.now(TZ_ISTANBUL).weekday() == 0:
        run_weekly(state, snapshot)

    return daily_ok


if __name__ == "__main__":
    run()
