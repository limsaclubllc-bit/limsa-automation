"""
Telegram Bot modülü — bildirim gönderme ve komut alma.
Polling tabanlıdır; GitHub Actions her çalıştığında bekleyen komutları işler.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from . import config_loader as cfg
from .logger import get_logger

log = get_logger("telegram")

BASE = "https://api.telegram.org/bot"


def _call(method: str, params: dict = None) -> dict:
    token = cfg.TELEGRAM_BOT_TOKEN
    if not token:
        log.warning("TELEGRAM_BOT_TOKEN tanımlı değil, atlanıyor")
        return {}
    url  = f"{BASE}{token}/{method}"
    data = urllib.parse.urlencode(params or {}).encode()
    req  = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        log.error("Telegram %s → %s: %s", method, e.code, e.read().decode())
        return {}
    except Exception as e:
        log.error("Telegram hata: %s", e)
        return {}


def send(text: str, chat_id: str = None, parse_mode: str = "HTML") -> bool:
    cid = chat_id or cfg.TELEGRAM_CHAT_ID
    if not cid:
        log.warning("TELEGRAM_CHAT_ID tanımlı değil")
        return False
    result = _call("sendMessage", {
        "chat_id":    cid,
        "text":       text,
        "parse_mode": parse_mode,
    })
    ok = result.get("ok", False)
    if not ok:
        log.error("Telegram mesaj gönderilemedi: %s", result)
    return ok


def send_order_alert(platform: str, order_id: str, customer: str,
                     amount: str, currency: str = "USD") -> bool:
    text = (
        f"🛍 <b>YENİ SİPARİŞ</b>\n"
        f"Platform: <b>{platform}</b>\n"
        f"Sipariş #: <code>{order_id}</code>\n"
        f"Müşteri: {customer}\n"
        f"Tutar: <b>{amount} {currency}</b>"
    )
    return send(text)


def send_low_stock_alert(product_name: str, variant: str,
                         quantity: int, platform: str) -> bool:
    emoji = "🔴" if quantity <= 2 else "🟡"
    text = (
        f"{emoji} <b>KRİTİK STOK</b>\n"
        f"Ürün: {product_name}\n"
        f"Varyant: {variant}\n"
        f"Stok: <b>{quantity} adet</b>\n"
        f"Platform: {platform}"
    )
    return send(text)


def send_error_alert(module: str, error: str) -> bool:
    text = (
        f"❌ <b>SİSTEM HATASI</b>\n"
        f"Modül: {module}\n"
        f"Hata: <code>{error[:300]}</code>"
    )
    return send(text)


def send_daily_summary(summary: str) -> bool:
    return send(f"📊 <b>GÜNLÜK ÖZET</b>\n\n{summary}")


def get_updates(offset: int = 0) -> list:
    """Bekleyen Telegram mesajlarını çek."""
    result = _call("getUpdates", {"offset": offset, "timeout": 0, "limit": 10})
    return result.get("result", [])


def process_commands(state: dict) -> dict:
    """
    Bekleyen bot komutlarını işle.
    state["telegram_offset"] son işlenen update_id'yi tutar.
    Komut yanıtları çağırana döner (komut, yanıt metni üretimini scheduler yapar).
    """
    offset  = state.get("telegram_offset", 0)
    updates = get_updates(offset)
    commands = []
    for u in updates:
        offset = u["update_id"] + 1
        msg    = u.get("message", {})
        text   = msg.get("text", "")
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if text.startswith("/"):
            commands.append({"command": text.split()[0].lower(),
                             "args":    text.split()[1:],
                             "chat_id": chat_id})
            log.info("Telegram komutu: %s", text)
    state["telegram_offset"] = offset
    return {"commands": commands, "state": state}
