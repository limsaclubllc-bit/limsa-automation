"""
Telegram komut işleyici.
GitHub Actions her çalışmada bu task'ı çağırır; bekleyen komutları işler.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from modules.telegram_bot   import process_commands, send
from modules.shopify_api    import ShopifyAPI
from modules.trendyol_api   import TrendyolAPI
from modules.stripe_api     import StripeAPI
from modules import state_manager as sm
from modules.currency        import get_usd_try_rate
from modules.config_loader  import TZ_ISTANBUL, LOW_STOCK_THRESHOLD
from modules.logger          import get_logger

log = get_logger("telegram_handler")

HELP_TEXT = """
<b>Limsa Club Bot Komutları</b>

/durum — Sistem bağlantı kontrolü
/siparisler — Son 5 sipariş
/stok — Düşük stok uyarıları
/gelir — Finansal özet
/kur — Güncel USD/TRY kuru
/rapor — Anlık özet raporu
/yardim — Bu menü
"""


def _ping_one(name_cls: tuple) -> str:
    name, api_cls = name_cls
    try:
        ok = api_cls().ping()
        return f"{'✅' if ok else '❌'} {name}: {'OK' if ok else 'HATA'}"
    except Exception as e:
        return f"❌ {name}: {e}"


def _cmd_durum() -> str:
    targets = [("Shopify", ShopifyAPI), ("Trendyol", TrendyolAPI), ("Stripe", StripeAPI)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(_ping_one, targets))
    return "<b>Sistem Durum Kontrolü</b>\n\n" + "\n".join(results)


def _cmd_siparisler() -> str:
    try:
        api    = ShopifyAPI()
        orders = api.get_orders(status="any", limit=5)
        if not orders:
            return "Henüz sipariş yok."
        lines = ["<b>Son 5 Shopify Siparişi</b>\n"]
        for o in orders:
            lines.append(
                f"#{o.get('name','')} — {o.get('total_price','')} {o.get('currency','')} "
                f"| {o.get('financial_status','')} | {o.get('created_at','')[:10]}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Sipariş listesi alınamadı: {e}"


def _cmd_stok() -> str:
    try:
        api      = ShopifyAPI()
        products = api.get_products()
        low      = []
        for p in products:
            for v in p.get("variants", []):
                qty = v.get("inventory_quantity", 0) or 0
                if qty <= LOW_STOCK_THRESHOLD:
                    low.append(f"• {p['title']} / {v['title']}: <b>{qty} adet</b>")
        if not low:
            return "✅ Tüm ürünlerde stok yeterli."
        return "<b>Düşük Stok Uyarıları</b>\n\n" + "\n".join(low[:20])
    except Exception as e:
        return f"Stok bilgisi alınamadı: {e}"


def _cmd_gelir() -> str:
    try:
        api    = StripeAPI()
        bal    = api.get_balance()
        weekly = api.get_weekly_revenue()
        return (
            f"<b>Finansal Özet</b>\n\n"
            f"Stripe bakiye: <b>${bal['available'].get('USD',0):.2f}</b>\n"
            f"Son 7 gün ciro: <b>${weekly['total_usd']:.2f}</b>\n"
            f"Son 7 gün sipariş: <b>{weekly['order_count']}</b> adet\n"
            f"Ortalama sipariş: <b>${weekly['avg_order_usd']:.2f}</b>"
        )
    except Exception as e:
        return f"Finansal bilgi alınamadı: {e}"


def _cmd_kur() -> str:
    try:
        rate = get_usd_try_rate()
        now  = datetime.now(TZ_ISTANBUL).strftime("%d.%m.%Y %H:%M")
        return (
            f"<b>Güncel Döviz Kuru</b>\n\n"
            f"1 USD = <b>{rate:.4f} TRY</b>\n"
            f"Kaynak: Frankfurter API\n"
            f"Güncelleme: {now}"
        )
    except Exception as e:
        return f"Kur bilgisi alınamadı: {e}"


def _cmd_rapor() -> str:
    try:
        sh_api = ShopifyAPI()
        st_api = StripeAPI()

        now       = datetime.now(TZ_ISTANBUL)
        month_min = now.replace(day=1, hour=0, minute=0, second=0).isoformat()
        orders    = sh_api.get_orders(status="any", limit=250, created_at_min=month_min)
        revenue   = sum(float(o.get("total_price",0)) for o in orders)
        balance   = st_api.get_balance()
        weekly    = st_api.get_weekly_revenue()

        return (
            f"<b>Anlık Rapor — {now.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
            f"Bu ay Shopify:\n"
            f"  {len(orders)} sipariş / ${revenue:.2f}\n\n"
            f"Stripe (7 gün): ${weekly['total_usd']:.2f}\n"
            f"Stripe bakiye: ${balance['available'].get('USD',0):.2f}"
        )
    except Exception as e:
        return f"Rapor oluşturulamadı: {e}"


COMMAND_MAP = {
    "/durum":     _cmd_durum,
    "/siparisler":_cmd_siparisler,
    "/stok":      _cmd_stok,
    "/gelir":     _cmd_gelir,
    "/kur":       _cmd_kur,
    "/rapor":     _cmd_rapor,
    "/yardim":    lambda: HELP_TEXT,
    "/start":     lambda: HELP_TEXT,
}


def run(state: dict = None, snapshot: dict = None) -> dict:
    if state is None:
        state, snapshot = sm.load()

    result   = process_commands(state)
    commands = result["commands"]
    state    = result["state"]

    if not commands:
        log.info("Telegram: İşlenecek komut yok")
        sm.save(state, snapshot)
        return {"processed": 0, "state": state}

    processed = 0
    for cmd in commands:
        command = cmd["command"]
        chat_id = cmd["chat_id"]
        log.info("Komut işleniyor: %s (chat: %s)", command, chat_id)

        handler = COMMAND_MAP.get(command)
        if handler:
            try:
                reply = handler()
                send(reply, chat_id=chat_id)
                processed += 1
            except Exception as e:
                log.error("Komut hatası %s: %s", command, e)
                send(f"❌ Hata: {e}", chat_id=chat_id)
        else:
            send(f"Bilinmeyen komut: {command}\n\n{HELP_TEXT}", chat_id=chat_id)

    sm.save(state, snapshot)
    log.info("Telegram: %d komut işlendi", processed)
    return {"processed": processed, "state": state}


if __name__ == "__main__":
    run()
