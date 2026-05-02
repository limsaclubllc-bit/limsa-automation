"""
Limsa Club — Ana Orkestratör
Yerel PC'de veya doğrudan çalıştırılabilir.
GitHub Actions'ta her workflow ayrı bir task'ı çağırır.

Kullanım:
  python scheduler.py --task order_sync
  python scheduler.py --task stock_sync
  python scheduler.py --task daily_report
  python scheduler.py --task telegram
  python scheduler.py --task all          # tüm görevler
  python scheduler.py --task ping         # bağlantı testi
"""

import sys
import argparse
from datetime import datetime
from modules.logger import get_logger

log = get_logger("scheduler")


def run_task(task: str) -> int:
    """Görevi çalıştır, 0=başarı döndür."""
    log.info("=" * 60)
    log.info("GÖREV BAŞLADI: %s — %s",
             task, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    try:
        if task == "order_sync":
            from tasks.order_sync import run
            result = run()
            log.info("Sipariş sync: %d yeni sipariş", len(result.get("new_orders", [])))

        elif task == "stock_sync":
            from tasks.stock_sync import run
            result = run()
            log.info("Stok sync: %d güncelleme, %d düşük stok",
                     result.get("trendyol_updated", 0),
                     len(result.get("low_stock_alerts", [])))

        elif task == "daily_report":
            from tasks.daily_report import run
            ok = run()
            log.info("Günlük rapor: %s", "OK" if ok else "HATA")
            return 0 if ok else 1

        elif task == "telegram":
            from tasks.telegram_handler import run
            result = run()
            log.info("Telegram: %d komut işlendi", result.get("processed", 0))

        elif task == "ping":
            from modules.trendyol_api  import TrendyolAPI
            from modules.shopify_api   import ShopifyAPI
            from modules.stripe_api    import StripeAPI
            apis = [("Trendyol", TrendyolAPI),
                    ("Shopify",  ShopifyAPI),
                    ("Stripe",   StripeAPI)]
            all_ok = True
            for name, cls in apis:
                ok = cls().ping()
                status = "✅ OK" if ok else "❌ HATA"
                print(f"  {status} — {name}")
                if not ok:
                    all_ok = False
            return 0 if all_ok else 1

        elif task == "all":
            from tasks.order_sync    import run as order_run
            from tasks.stock_sync    import run as stock_run
            from tasks.telegram_handler import run as tg_run
            order_run()
            stock_run()
            tg_run()
            log.info("Tüm görevler tamamlandı")

        else:
            log.error("Bilinmeyen görev: %s", task)
            print(f"Geçerli görevler: order_sync, stock_sync, daily_report, telegram, ping, all")
            return 1

        log.info("GÖREV TAMAMLANDI: %s", task)
        return 0

    except Exception as e:
        log.error("GÖREV HATASI [%s]: %s", task, e, exc_info=True)
        try:
            from modules.telegram_bot import send_error_alert
            send_error_alert(task, str(e))
        except Exception:
            pass
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Limsa Club Otomasyon Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--task", "-t",
        choices=["order_sync", "stock_sync", "daily_report",
                 "telegram", "ping", "all"],
        required=True,
        help="Çalıştırılacak görev",
    )
    args = parser.parse_args()
    sys.exit(run_task(args.task))


if __name__ == "__main__":
    main()
