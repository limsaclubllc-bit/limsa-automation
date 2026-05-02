"""
Trendyol Seller API istemcisi.
Docs: https://developers.trendyol.com/tr/docs
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional
from . import config_loader as cfg
from .logger import get_logger

log = get_logger("trendyol")

BASE_URL = "https://api.trendyol.com/sapigw"


class TrendyolAPI:
    def __init__(self):
        self.supplier_id    = cfg.TRENDYOL_SUPPLIER_ID
        self.token          = cfg.TRENDYOL_TOKEN
        integration_code    = cfg.TRENDYOL_INTEGRATION_CODE or "SelfIntegration"
        self.headers = {
            "Authorization": f"Basic {self.token}",
            "User-Agent":    f"{self.supplier_id} - {integration_code}",
            "Content-Type":  "application/json",
        }

    def _request(self, method: str, endpoint: str, body: dict = None) -> dict:
        url  = f"{BASE_URL}{endpoint}"
        data = json.dumps(body).encode() if body else None
        req  = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            log.error("HTTP %s %s → %s: %s", method, endpoint, e.code, detail)
            raise
        except Exception as e:
            log.error("Request error %s %s: %s", method, endpoint, e)
            raise

    def get_orders(self, status: str = None, page: int = 0, size: int = 50) -> dict:
        """Siparişleri çek. status: Created, Picking, Invoiced, Shipped, Delivered, Cancelled"""
        params = f"?orderByField=PackageLastModifiedDate&orderByDirection=DESC&page={page}&size={size}"
        if status:
            params += f"&status={status}"
        return self._request("GET", f"/suppliers/{self.supplier_id}/orders{params}")

    def get_new_orders(self, since_timestamp_ms: int = None) -> list:
        """Son X ms'den bu yana gelen yeni siparişleri döndür."""
        data = self.get_orders(page=0, size=100)
        orders = data.get("content", [])
        if since_timestamp_ms:
            orders = [o for o in orders
                      if o.get("orderDate", 0) > since_timestamp_ms]
        return orders

    def update_tracking(self, shipment_package_id: str, tracking_number: str,
                        cargo_provider_name: str = "Yurtiçi Kargo") -> dict:
        body = {
            "lines": [{"barcode": "", "quantity": 1}],
            "params": {},
            "cargoProviderName": cargo_provider_name,
            "trackingNumber": tracking_number,
        }
        return self._request("PUT",
            f"/suppliers/{self.supplier_id}/shipment-packages/{shipment_package_id}",
            body)

    def get_products(self, page: int = 0, size: int = 50,
                     barcode: str = None) -> dict:
        params = f"?page={page}&size={size}"
        if barcode:
            params += f"&barcode={barcode}"
        return self._request("GET", f"/suppliers/{self.supplier_id}/products{params}")

    MAX_PAGES = 100  # API yanıtında totalPages hatalıysa sonsuz döngü önlemi

    def get_all_products(self) -> list:
        all_products, page = [], 0
        while page < self.MAX_PAGES:
            data = self.get_products(page=page, size=100)
            content = data.get("content", [])
            all_products.extend(content)
            total_pages = data.get("totalPages", 1)
            if page + 1 >= total_pages:
                break
            page += 1
            time.sleep(0.3)
        log.info("Trendyol toplam %d ürün çekildi", len(all_products))
        return all_products

    def update_price_and_stock(self, items: list) -> dict:
        """
        items = [
            {"barcode": "SKU123", "quantity": 10, "salePrice": 1299.99,
             "listPrice": 1499.99}
        ]
        """
        body = {"items": items}
        return self._request("POST",
            f"/suppliers/{self.supplier_id}/products/price-and-inventory", body)

    def update_single_product_stock(self, barcode: str, quantity: int,
                                    sale_price: float, list_price: float) -> dict:
        return self.update_price_and_stock([{
            "barcode":   barcode,
            "quantity":  quantity,
            "salePrice": sale_price,
            "listPrice": list_price,
        }])

    def get_payments(self, start_date: str = None, end_date: str = None) -> dict:
        """start_date / end_date: 'YYYY-MM-DD' formatında"""
        params = "?"
        if start_date:
            params += f"startDate={start_date}&"
        if end_date:
            params += f"endDate={end_date}"
        return self._request("GET",
            f"/suppliers/{self.supplier_id}/finance/che-payments{params.rstrip('?&')}")

    def ping(self) -> bool:
        try:
            data = self.get_products(page=0, size=1)
            log.info("Trendyol bağlantı OK — toplam ürün: %s", data.get("totalElements"))
            return True
        except Exception as e:
            log.error("Trendyol bağlantı HATA: %s", e)
            return False
