"""
Shopify Admin REST API istemcisi (otomasyon scriptleri için).
Not: MCP bağlantısı Claude Code içindir; bu modül GitHub Actions'ta çalışır.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional
from . import config_loader as cfg
from .logger import get_logger

log = get_logger("shopify")


class ShopifyAPI:
    def __init__(self):
        self.store   = cfg.SHOPIFY_STORE_URL
        self.token   = cfg.SHOPIFY_ACCESS_TOKEN
        self.version = cfg.SHOPIFY_API_VERSION
        self.base    = f"https://{self.store}/admin/api/{self.version}"
        self.headers = {
            "X-Shopify-Access-Token": self.token,
            "Content-Type":           "application/json",
        }

    def _request(self, method: str, path: str, body: dict = None) -> dict:
        url  = f"{self.base}{path}"
        data = json.dumps(body).encode() if body else None
        req  = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            log.error("HTTP %s %s → %s: %s", method, path, e.code, detail)
            raise

    # ── SİPARİŞLER ────────────────────────────────────────────────────────────

    def get_orders(self, status: str = "any", limit: int = 50,
                   since_id: int = None, created_at_min: str = None) -> list:
        params = f"?status={status}&limit={limit}"
        if since_id:
            params += f"&since_id={since_id}"
        if created_at_min:
            params += f"&created_at_min={urllib.parse.quote(created_at_min)}"
        data = self._request("GET", f"/orders.json{params}")
        return data.get("orders", [])

    def get_order(self, order_id: int) -> dict:
        data = self._request("GET", f"/orders/{order_id}.json")
        return data.get("order", {})

    def get_products(self, limit: int = 250) -> list:
        data = self._request("GET", f"/products.json?limit={limit}&status=active")
        return data.get("products", [])

    def get_product(self, product_id: int) -> dict:
        data = self._request("GET", f"/products/{product_id}.json")
        return data.get("product", {})

    def update_variant_inventory(self, variant_id: int, quantity: int) -> dict:
        body = {"variant": {"id": variant_id, "inventory_quantity": quantity}}
        return self._request("PUT", f"/variants/{variant_id}.json", body)

    def update_variant_price(self, variant_id: int, price: str,
                              compare_at_price: str = None) -> dict:
        v = {"id": variant_id, "price": price}
        if compare_at_price:
            v["compare_at_price"] = compare_at_price
        return self._request("PUT", f"/variants/{variant_id}.json", {"variant": v})

    def get_inventory_levels(self, inventory_item_ids: list) -> list:
        ids = ",".join(str(i) for i in inventory_item_ids)
        data = self._request("GET", f"/inventory_levels.json?inventory_item_ids={ids}")
        return data.get("inventory_levels", [])

    def set_inventory_level(self, inventory_item_id: int,
                             location_id: int, available: int) -> dict:
        body = {
            "location_id":         location_id,
            "inventory_item_id":   inventory_item_id,
            "available":           available,
        }
        return self._request("POST", "/inventory_levels/set.json", body)

    def get_locations(self) -> list:
        data = self._request("GET", "/locations.json")
        return data.get("locations", [])

    def ping(self) -> bool:
        try:
            self.get_products(limit=1)
            log.info("Shopify bağlantı OK")
            return True
        except Exception as e:
            log.error("Shopify bağlantı HATA: %s", e)
            return False
