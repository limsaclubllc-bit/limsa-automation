"""
Döviz kuru modülü — USD/TRY ve diğer kurlar.
Ücretsiz API'ler kullanılır; başarısız olursa config'deki sabit kur devreye girer.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from . import config_loader as cfg
from .logger import get_logger

log = get_logger("currency")

CACHE_FILE = Path(__file__).parent.parent / "data" / "exchange_rates.json"
CACHE_TTL_HOURS = 4

# Görev süresi boyunca disk I/O tekrarını önler
_MEM_CACHE: dict = {}


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            updated = datetime.fromisoformat(data.get("updated_at", "2000-01-01"))
            if datetime.utcnow() - updated < timedelta(hours=CACHE_TTL_HOURS):
                return data
        except Exception:
            pass
    return {}


def _save_cache(data: dict):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    data["updated_at"] = datetime.utcnow().isoformat()
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_from_ecb() -> dict:
    """Avrupa Merkez Bankası'ndan kur çek (tamamen ücretsiz, EUR bazlı)."""
    url = "https://api.frankfurter.app/latest?from=USD"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        rates = data.get("rates", {})
        log.info("Frankfurter API'den kur alındı: USD/TRY=%.4f", rates.get("TRY", 0))
        return rates
    except Exception as e:
        log.warning("Frankfurter API başarısız: %s", e)
        return {}


def _fetch_from_freecurrencyapi(api_key: str) -> dict:
    url = f"https://api.freecurrencyapi.com/v1/latest?apikey={api_key}&base_currency=USD"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        rates = data.get("data", {})
        log.info("FreeCurrencyAPI'den kur alındı: USD/TRY=%.4f", rates.get("TRY", 0))
        return rates
    except Exception as e:
        log.warning("FreeCurrencyAPI başarısız: %s", e)
        return {}


def _fallback_rate() -> float:
    return cfg.get_settings()["pricing"]["fallback_rate"]


def get_rates() -> dict:
    if _MEM_CACHE.get("rates"):
        return _MEM_CACHE["rates"]

    cache = _load_cache()
    if cache.get("rates"):
        _MEM_CACHE["rates"] = cache["rates"]
        return cache["rates"]

    rates = {}
    api_key = cfg.CURRENCY_API_KEY
    if api_key:
        rates = _fetch_from_freecurrencyapi(api_key)
    if not rates:
        rates = _fetch_from_ecb()

    if rates:
        _save_cache({"rates": rates})
        _MEM_CACHE["rates"] = rates
        return rates

    fallback = _fallback_rate()
    log.warning("Kur alınamadı, sabit kur kullanılıyor: %.2f", fallback)
    return {"TRY": fallback, "EUR": 0.93, "GBP": 0.79}


def usd_to_try(amount_usd: float) -> float:
    rate = get_rates().get("TRY", _fallback_rate())
    return round(amount_usd * rate, 2)


def try_to_usd(amount_try: float) -> float:
    rate = get_rates().get("TRY", _fallback_rate())
    return round(amount_try / rate, 2) if rate else 0


def get_usd_try_rate() -> float:
    return get_rates().get("TRY", _fallback_rate())
