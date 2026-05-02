"""
Stripe finansal takip modülü.
stripe kütüphanesi yerine doğrudan HTTP kullanılır (bağımlılığı azaltmak için).
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import base64
from datetime import datetime, timedelta
from . import config_loader as cfg
from .logger import get_logger

log = get_logger("stripe")

BASE_URL = "https://api.stripe.com/v1"


class StripeAPI:
    def __init__(self):
        self.secret_key = cfg.STRIPE_SECRET_KEY
        cred = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {cred}",
            "Content-Type":  "application/x-www-form-urlencoded",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{BASE_URL}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            log.error("Stripe GET %s → %s: %s", path, e.code, e.read().decode())
            raise

    def get_balance(self) -> dict:
        data = self._get("/balance")
        available = {b["currency"].upper(): b["amount"] / 100
                     for b in data.get("available", [])}
        pending   = {b["currency"].upper(): b["amount"] / 100
                     for b in data.get("pending", [])}
        log.info("Stripe bakiye — available: %s, pending: %s", available, pending)
        return {"available": available, "pending": pending}

    def get_recent_payments(self, days: int = 7, limit: int = 100) -> list:
        since = int((datetime.utcnow() - timedelta(days=days)).timestamp())
        data  = self._get("/payment_intents", {
            "limit":            limit,
            "created[gte]":     since,
        })
        payments = data.get("data", [])
        succeeded = [p for p in payments if p.get("status") == "succeeded"]
        log.info("Stripe son %d gün: %d başarılı ödeme", days, len(succeeded))
        return succeeded

    def get_payouts(self, limit: int = 10) -> list:
        data = self._get("/payouts", {"limit": limit})
        return data.get("data", [])

    def get_weekly_revenue(self) -> dict:
        payments  = self.get_recent_payments(days=7)
        total_usd = sum(p.get("amount", 0) for p in payments
                        if p.get("currency", "").lower() == "usd") / 100
        count     = len(payments)
        return {
            "period":        "last_7_days",
            "total_usd":     round(total_usd, 2),
            "order_count":   count,
            "avg_order_usd": round(total_usd / count, 2) if count else 0,
        }

    def ping(self) -> bool:
        try:
            self.get_balance()
            return True
        except Exception as e:
            log.error("Stripe ping HATA: %s", e)
            return False
