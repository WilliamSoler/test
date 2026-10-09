"""Minimal client for Polymarket's public (no-auth) APIs, with retries and a disk cache.

Endpoints used:
  gamma-api.polymarket.com  /markets, /events          market metadata, fee schedule, volume
  data-api.polymarket.com   /trades                    executed trades (taker rows, or taker + maker rows)
  clob.polymarket.com       /book, /prices-history     live order books, minute price history
  polymarket.com            /api/geoblock              whether the caller's IP is geo-blocked
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests

GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
SITE = "https://polymarket.com"

CACHE_DIR = Path(os.environ.get("PM_CACHE_DIR", Path(__file__).parent / ".cache"))
_session = requests.Session()
_session.headers["User-Agent"] = "pm-mm-feasibility-check/1.0"


def get(url: str, params: dict | list | None = None, cache: bool = False, retries: int = 5):
    """GET JSON. `cache=True` stores the response on disk (only use for immutable data, e.g. closed markets)."""
    key = None
    if cache:
        key = hashlib.sha1((url + json.dumps(params, sort_keys=True, default=str)).encode()).hexdigest()
        path = CACHE_DIR / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())
    delay = 1.0
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code}")
            r.raise_for_status()
            data = r.json()
            break
        except (requests.RequestException, ValueError):
            if attempt == retries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    if cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{key}.json").write_text(json.dumps(data))
    return data


def fee(shares: float, price: float, schedule: dict | None) -> float:
    """Taker fee in USDC: shares * rate * (p * (1 - p)) ** exponent (docs.polymarket.com fee formula)."""
    if not schedule:
        return 0.0
    return shares * schedule["rate"] * (price * (1 - price)) ** schedule.get("exponent", 1)


def event_by_slug(slug: str, cache: bool = False):
    d = get(f"{GAMMA}/events", {"slug": slug}, cache=cache)
    return d[0] if d else None


def market_trades(condition_id: str, taker_only: bool = True, cache: bool = False) -> list[dict]:
    """All trades for one market (data-api caps offset at 10,000, so very busy markets are truncated)."""
    out = []
    for offset in range(0, 10_001, 500):
        page = get(f"{DATA}/trades", {"market": condition_id, "limit": 500, "offset": offset,
                                      "takerOnly": str(taker_only).lower()}, cache=cache)
        if not isinstance(page, list) or not page:
            break
        out.extend(page)
        if len(page) < 500:
            break
    return out


def price_history(token_id: str, start: int, end: int, cache: bool = False) -> list[dict]:
    d = get(f"{CLOB}/prices-history", {"market": token_id, "startTs": start, "endTs": end, "fidelity": 1},
            cache=cache)
    return d.get("history", [])
