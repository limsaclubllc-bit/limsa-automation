"""
Durum yöneticisi — son işlenen sipariş ID'leri, offset'ler ve sayaçlar.
data/state.json dosyasında saklanır; GitHub Actions bu dosyayı commit eder.
"""

import copy
import json
from pathlib import Path
from datetime import datetime
from .logger import get_logger

log = get_logger("state")

STATE_FILE = Path(__file__).parent.parent / "data" / "state.json"

_DEFAULT = {
    "last_shopify_order_id":   0,
    "last_trendyol_order_ts":  0,
    "last_etsy_order_id":      0,
    "telegram_offset":         0,
    "last_run": {
        "order_sync":    None,
        "stock_sync":    None,
        "daily_report":  None,
        "weekly_report": None,
    },
    "stats": {
        "total_shopify_orders":  0,
        "total_trendyol_orders": 0,
        "total_etsy_orders":     0,
    },
    "updated_at": None,
}


def load() -> tuple[dict, dict]:
    """State ve orijinal snapshot döndürür. Değişiklik tespiti için snapshot kullanılır."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            for k, v in _DEFAULT.items():
                if k not in data:
                    data[k] = v
                elif isinstance(v, dict):
                    for kk, vv in v.items():
                        if kk not in data[k]:
                            data[k][kk] = vv
            snapshot = copy.deepcopy(data)
            return data, snapshot
        except Exception as e:
            log.error("State yüklenemedi: %s — sıfırlanıyor", e)
    fresh = copy.deepcopy(_DEFAULT)
    return fresh, copy.deepcopy(fresh)


def save(state: dict, snapshot: dict = None) -> bool:
    """Değişiklik yoksa diske yazmaz; True=kaydedildi, False=atlandı."""
    # updated_at'ı karşılaştırmadan çıkar
    check = {k: v for k, v in state.items() if k != "updated_at"}
    orig  = {k: v for k, v in (snapshot or {}).items() if k != "updated_at"}
    if snapshot is not None and check == orig:
        log.debug("State değişmedi, kaydedilmiyor")
        return False
    state["updated_at"] = datetime.utcnow().isoformat()
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    log.debug("State kaydedildi")
    return True


def mark_run(task_name: str, state: dict) -> dict:
    state.setdefault("last_run", {})[task_name] = datetime.utcnow().isoformat()
    return state


def get_last_run(task_name: str, state: dict) -> str | None:
    return state.get("last_run", {}).get(task_name)
