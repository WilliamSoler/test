"""How big is the maker-rebate pool really?

1. Pulls every active market plus every market that closed in the last 24h from the Gamma API and records its
   fee schedule (feesEnabled, feeType, rate, rebateRate), 24h volume and liquidity-reward budget.
2. Samples the most recent ~10k taker trades platform-wide (data-api cap) and prices each one with its market's
   fee schedule, to measure the average fee per share actually traded, by fee type.
3. Estimates 24h taker fees = 24h share volume x measured fee/share, and the rebate pool = fees x rebateRate.
   Annualised x365 and compared with the $25-250M/yr claim.

Note: Gamma `volume` / `volume24hr` count *shares* (checked against summed trade sizes), not USDC notional.
"""
from __future__ import annotations

import collections
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

import pm_api

RESULTS = Path(__file__).parent / "results"


def page_markets(params: dict) -> list[dict]:
    """Keyset pagination (the plain /markets endpoint refuses offsets above ~2000)."""
    out, cursor = [], None
    while True:
        d = pm_api.get(f"{pm_api.GAMMA}/markets/keyset",
                       {**params, "limit": 100, **({"after_cursor": cursor} if cursor else {})})
        out.extend(d.get("markets") or [])
        cursor = d.get("next_cursor")
        if not cursor or not d.get("markets"):
            return out


def market_row(m: dict, now: int, closed_recent: bool) -> dict:
    sched = m.get("feeSchedule") if m.get("feesEnabled") else None
    try:
        p = float(m.get("lastTradePrice") or json.loads(m.get("outcomePrices") or "[]")[0])
    except (ValueError, IndexError, TypeError):
        p = None
    vol24 = float(m.get("volume24hr") or 0)
    if closed_recent and not vol24:
        # short-lived markets: whole life inside the last 24h -> total volume is the 24h volume
        start = pd.Timestamp(m.get("startDate") or m.get("createdAt") or 0).timestamp()
        if now - start < 2 * 86400:
            vol24 = float(m.get("volume") or 0)
    rewards = sum(float(r.get("rewardsDailyRate") or 0) for r in (m.get("clobRewards") or []))
    return {
        "conditionId": m.get("conditionId"), "slug": m.get("slug"), "closed_recent": closed_recent,
        "feeType": m.get("feeType") if sched else "no_fee", "rate": (sched or {}).get("rate", 0.0),
        "rebateRate": (sched or {}).get("rebateRate", 0.0), "exponent": (sched or {}).get("exponent", 1),
        "price": p, "volume24h_shares": vol24, "liquidity_rewards_per_day": rewards,
    }


def trade_sample() -> list[dict]:
    with ThreadPoolExecutor(6) as ex:
        pages = ex.map(lambda off: pm_api.get(f"{pm_api.DATA}/trades",
                                              {"limit": 500, "offset": off, "takerOnly": "true"}),
                       range(0, 10_001, 500))
        trades = [t for p in pages if isinstance(p, list) for t in p]
    # pages shift while we read; drop duplicates
    seen, out = set(), []
    for t in trades:
        k = (t["transactionHash"], t["asset"], t["proxyWallet"], t["size"])
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out


def schedules_for(condition_ids: set[str], known: dict) -> dict:
    missing = [c for c in condition_ids if c not in known]
    for i in range(0, len(missing), 50):
        batch = missing[i:i + 50]
        for closed in ("false", "true"):
            ms = pm_api.get(f"{pm_api.GAMMA}/markets", [("condition_ids", c) for c in batch] + [("closed", closed)])
            for m in ms or []:
                known[m["conditionId"]] = market_row(m, int(time.time()), False)
    return known


def main():
    now = int(time.time())
    RESULTS.mkdir(exist_ok=True)
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 86400))
    active = page_markets({"active": "true", "closed": "false"})
    closed = page_markets({"closed": "true", "end_date_min": since})
    print(f"active markets: {len(active)}, closed in last 24h: {len(closed)}")
    rows = {}
    for m in closed:
        rows[m["conditionId"]] = market_row(m, now, True)
    for m in active:
        rows[m["conditionId"]] = market_row(m, now, False)
    mk = pd.DataFrame(rows.values())

    # --- fee per share actually paid, from a platform-wide trade sample ---
    trades = trade_sample()
    known = {c: r for c, r in rows.items()}
    schedules_for({t["conditionId"] for t in trades}, known)
    tr = []
    for t in trades:
        r = known.get(t["conditionId"])
        if not r:
            continue
        q, p = float(t["size"]), float(t["price"])
        f = q * r["rate"] * (p * (1 - p)) ** r["exponent"]
        tr.append({"feeType": r["feeType"], "shares": q, "notional": q * p, "fee": f,
                   "rebate": f * r["rebateRate"], "ts": t["timestamp"], "slug": t.get("slug", "")})
    tr = pd.DataFrame(tr)
    span_min = (tr.ts.max() - tr.ts.min()) / 60
    g = tr.groupby("feeType")
    sample = pd.DataFrame({"trades": g.size(), "shares": g.shares.sum(), "notional_usd": g.notional.sum(),
                           "fees_usd": g.fee.sum(), "rebates_usd": g.rebate.sum()})
    sample["fee_per_share"] = sample.fees_usd / sample.shares
    sample["fee_pct_notional"] = 100 * sample.fees_usd / sample.notional_usd
    print(f"\n=== trade sample: {len(tr)} taker trades over {span_min:.1f} min ===")
    print(sample.round(4))
    sample_annual_fees = tr.fee.sum() / span_min * 60 * 24 * 365
    sample_annual_rebates = tr.rebate.sum() / span_min * 60 * 24 * 365

    # --- 24h estimate from Gamma volumes ---
    fps = sample.fee_per_share.to_dict()
    mk["fee_per_share_est"] = [
        (r.rate * (r.price * (1 - r.price)) ** r.exponent
         if (not r.closed_recent and r.price is not None and 0 < r.price < 1) else fps.get(r.feeType, 0.0))
        for r in mk.itertuples()]
    mk["fees24h_est"] = mk.volume24h_shares * mk.fee_per_share_est
    mk["rebates24h_est"] = mk.fees24h_est * mk.rebateRate
    g = mk.groupby("feeType")
    day = pd.DataFrame({"markets": g.size(), "volume24h_shares": g.volume24h_shares.sum(),
                        "taker_fees_24h_usd": g.fees24h_est.sum(), "rebate_pool_24h_usd": g.rebates24h_est.sum(),
                        "liquidity_rewards_24h_usd": g.liquidity_rewards_per_day.sum()})
    day.loc["TOTAL"] = day.sum()
    day["rebate_pool_annualised_usd"] = day.rebate_pool_24h_usd * 365
    print("\n=== 24h estimate by fee type (Gamma volume x fee/share) ===")
    with pd.option_context("display.width", 200, "display.float_format", "{:,.0f}".format):
        print(day)

    summary = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "active_markets": len(active), "closed_last_24h": len(closed),
        "fee_schedules_seen": collections.Counter(
            json.dumps({"feeType": r["feeType"], "rate": r["rate"], "rebateRate": r["rebateRate"]})
            for r in rows.values()).most_common(),
        "taker_fees_24h_usd": float(day.loc["TOTAL", "taker_fees_24h_usd"]),
        "rebate_pool_24h_usd": float(day.loc["TOTAL", "rebate_pool_24h_usd"]),
        "rebate_pool_annualised_usd": float(day.loc["TOTAL", "rebate_pool_annualised_usd"]),
        "liquidity_rewards_24h_usd": float(day.loc["TOTAL", "liquidity_rewards_24h_usd"]),
        "trade_sample_minutes": float(span_min), "trade_sample_trades": len(tr),
        "trade_sample_annualised_fees_usd": float(sample_annual_fees),
        "trade_sample_annualised_rebates_usd": float(sample_annual_rebates),
    }
    stamp = time.strftime("%Y%m%d", time.gmtime(now))
    day.to_csv(RESULTS / f"fee_census_24h_{stamp}.csv")
    sample.to_csv(RESULTS / f"fee_trade_sample_{stamp}.csv")
    (RESULTS / f"fee_census_summary_{stamp}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "fee_schedules_seen"}, indent=2))
    print("fee schedules:", *summary["fee_schedules_seen"][:20], sep="\n  ")


if __name__ == "__main__":
    main()
