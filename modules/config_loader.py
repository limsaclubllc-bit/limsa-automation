"""
Ortam değişkenlerini ve settings.json'u yükler.
GitHub Actions'ta env vars Secrets'tan gelir; yerel çalışmada .env dosyasından.
"""

import os
import json
from datetime import timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def _load_dotenv():
    env_path = BASE_DIR / "config" / "credentials.env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and value and key not in os.environ:
            os.environ[key] = value

_load_dotenv()

def get_settings() -> dict:
    path = BASE_DIR / "config" / "settings.json"
    return json.loads(path.read_text(encoding="utf-8"))

def e(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

# Trendyol
TRENDYOL_SUPPLIER_ID   = e("TRENDYOL_SUPPLIER_ID", "1124622")
TRENDYOL_API_KEY       = e("TRENDYOL_API_KEY")
TRENDYOL_API_SECRET    = e("TRENDYOL_API_SECRET")
TRENDYOL_TOKEN         = e("TRENDYOL_TOKEN")

# Shopify
SHOPIFY_STORE_URL      = e("SHOPIFY_STORE_URL", "limsa.club")
SHOPIFY_ACCESS_TOKEN   = e("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_VERSION    = "2024-01"

# Stripe
STRIPE_SECRET_KEY      = e("STRIPE_SECRET_KEY")

# Gmail
GMAIL_SENDER           = e("GMAIL_SENDER", "info@limsa.club")
GMAIL_APP_PASSWORD     = e("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENT        = e("GMAIL_REPORT_RECIPIENT", "info@limsa.club")

# Telegram
TELEGRAM_BOT_TOKEN     = e("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID       = e("TELEGRAM_CHAT_ID")

# Etsy
ETSY_ACCESS_TOKEN      = e("ETSY_ACCESS_TOKEN")
ETSY_KEYSTRING         = e("ETSY_KEYSTRING")

# Currency
CURRENCY_API_KEY       = e("CURRENCY_API_KEY")

# Paylaşımlı sabitler
TZ_ISTANBUL            = timezone(timedelta(hours=3))
LOW_STOCK_THRESHOLD    = 5
CRITICAL_STOCK_THRESHOLD = 2
