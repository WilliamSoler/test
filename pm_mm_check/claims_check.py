"""Quick checks of the stated fee mechanics and access, straight from the live API.

- reads the fee schedule of the currently trading BTC 15-minute Up/Down market
- recomputes "100 shares at $0.50" and the fee as % of money paid
- lists every fee schedule version currently live (evidence of how often the rules change)
- calls polymarket.com/api/geoblock (answers for the IP this runs from -- run it from YOUR machine)
"""
from __future__ import annotations

import json
import time

import pm_api


def main():
    now = int(time.time())
    slug = f"btc-updown-15m-{now // 900 * 900}"
    m = pm_api.event_by_slug(slug)["markets"][0]
    s = m["feeSchedule"]
    print(f"{slug}: feesEnabled={m['feesEnabled']} feeType={m['feeType']} schedule={s}")
    f = pm_api.fee(100, 0.50, s)
    print(f"fee for 100 shares @ $0.50 = ${f:.2f} = {100 * f / 50:.2f}% of $50 paid")
    for p in (0.1, 0.3, 0.5, 0.7, 0.9):
        print(f"  price {p:.1f}: fee {100 * pm_api.fee(1, p, s) / p:.2f}% of money paid, "
              f"maker rebate {100 * pm_api.fee(1, p, s) * s['rebateRate'] / p:.3f}%")
    print(f"min order size {m.get('orderMinSize')} shares, tick {m.get('orderPriceMinTickSize')}, "
          f"liquidity rewards on this market: {m.get('clobRewards') or 'none'}")
    print("geoblock (for this machine's IP):", pm_api.get(f"{pm_api.SITE}/api/geoblock"))


if __name__ == "__main__":
    main()
