"""Who provides liquidity in the short crypto markets, and do they make money?

For a sample of resolved Up/Down markets, pulls *all* fill rows (taker + maker legs, data-api takerOnly=false),
drops the taker legs, and attributes every maker fill to its wallet. For each wallet:
  maker notional and share of all maker volume,
  P&L to resolution of its maker fills,
  estimated rebate = rebateRate x fee-equivalent of its fills (Polymarket's per-market pro-rata rule).

This shows how concentrated market making is (are a few professional firms doing it all?) and whether the
profits go to a few large makers or are spread across small ones.

Usage: python competition.py --lookback 15m:24,5m:12 --assets btc,eth
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

import pm_api
from maker_pnl_backtest import INTERVAL_SECONDS, windows

RESULTS = Path(__file__).parent / "results"


def process(win):
    asset, iv, slug, start = win
    ev = pm_api.event_by_slug(slug, cache=True)
    if not ev or not ev.get("markets"):
        return []
    m = ev["markets"][0]
    payouts = [float(x) for x in json.loads(m["outcomePrices"])]
    if not m.get("closed") or sorted(payouts) != [0.0, 1.0]:
        return []
    sched = m.get("feeSchedule") if m.get("feesEnabled") else None
    takers = pm_api.market_trades(m["conditionId"], taker_only=True, cache=True)
    fills = pm_api.market_trades(m["conditionId"], taker_only=False, cache=True)
    truncated = len(fills) >= 10_000
    taker_keys = {(t["transactionHash"], t["proxyWallet"], t["asset"], t["side"]) for t in takers}
    rows = []
    for f in fills:
        if (f["transactionHash"], f["proxyWallet"], f["asset"], f["side"]) in taker_keys:
            continue
        p, q = float(f["price"]), float(f["size"])
        payout = payouts[int(f["outcomeIndex"])]
        sign = 1 if f["side"] == "BUY" else -1  # maker bought (+1) or sold (-1) this token
        rows.append({"slug": slug, "asset": asset, "interval": iv, "wallet": f["proxyWallet"],
                     "name": f.get("name") or f.get("pseudonym") or "", "notional": p * q, "shares": q,
                     "pnl_resolution": sign * (payout - p) * q,
                     "rebate_est": pm_api.fee(q, p, sched) * (sched or {}).get("rebateRate", 0),
                     "truncated": truncated})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback", default="15m:24,5m:12")
    ap.add_argument("--assets", default="btc,eth")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    now = int(time.time())
    lookback = {k: float(v) for k, v in (x.split(":") for x in args.lookback.split(","))}
    wins = list(windows(args.assets.split(","), lookback, now))
    with ThreadPoolExecutor(args.workers) as ex:
        df = pd.DataFrame([r for rows in ex.map(process, wins) for r in rows])
    print(f"{df.slug.nunique()} markets, {len(df)} maker fills, {df.wallet.nunique()} distinct maker wallets, "
          f"{df[df.truncated].slug.nunique()} markets truncated at the 10k-row API cap")

    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d", time.gmtime(now))
    out = {}
    for key, sub in [("ALL", df)] + list(df.groupby(["interval", "asset"])):
        key = key if isinstance(key, str) else "/".join(key)
        w = sub.groupby("wallet").agg(name=("name", "first"), markets=("slug", "nunique"), fills=("shares", "size"),
                                      notional=("notional", "sum"), pnl_resolution=("pnl_resolution", "sum"),
                                      rebate_est=("rebate_est", "sum"))
        w["net"] = w.pnl_resolution + w.rebate_est
        w["share_pct"] = 100 * w.notional / w.notional.sum()
        w["net_bps"] = 1e4 * w.net / w.notional
        w = w.sort_values("notional", ascending=False)
        top = w.head(10)
        rest = w.iloc[10:]
        summary = {
            "markets": int(sub.slug.nunique()), "maker_wallets": len(w),
            "maker_notional_usd": round(w.notional.sum()),
            "top1_share_pct": round(w.share_pct.iloc[:1].sum(), 1),
            "top5_share_pct": round(w.share_pct.iloc[:5].sum(), 1),
            "top10_share_pct": round(w.share_pct.iloc[:10].sum(), 1),
            "hhi": round(float(((w.share_pct) ** 2).sum())),
            "wallets_over_1pct": int((w.share_pct > 1).sum()),
            "top10_net_usd": round(top.net.sum()), "top10_net_bps": round(1e4 * top.net.sum() / top.notional.sum(), 1),
            "rest_net_usd": round(rest.net.sum()),
            "rest_net_bps": round(1e4 * rest.net.sum() / max(rest.notional.sum(), 1), 1),
            "profitable_wallets_pct_of_top10": int((top.net > 0).sum()) * 10,
        }
        out[key] = summary
        if key == "ALL":
            rank = pd.Series(range(1, len(w) + 1), index=w.index)
            w["tier"] = pd.cut(rank, [0, 10, 50, 200, 1000, 10**9],
                               labels=["top 10", "11-50", "51-200", "201-1000", ">1000"])
            t = w.groupby("tier", observed=True).agg(wallets=("net", "size"), notional=("notional", "sum"),
                                                     pnl_resolution=("pnl_resolution", "sum"),
                                                     rebate_est=("rebate_est", "sum"), net=("net", "sum"),
                                                     profitable_pct=("net", lambda x: 100 * (x > 0).mean()))
            t["net_bps"] = 1e4 * t.net / t.notional
            t["share_pct"] = 100 * t.notional / t.notional.sum()
            t.round(1).to_csv(RESULTS / f"competition_tiers_{stamp}.csv")
            print("\nMaker wallets by volume rank:")
            print(t.round(1))
            w.head(25).round(2).to_csv(RESULTS / f"competition_top_makers_{stamp}.csv")
            print("\nTop 15 maker wallets (all sampled markets):")
            with pd.option_context("display.width", 200):
                print(w.head(15)[["name", "markets", "notional", "share_pct", "pnl_resolution", "rebate_est", "net",
                                  "net_bps"]].round(1))
    s = pd.DataFrame(out).T
    s.to_csv(RESULTS / f"competition_summary_{stamp}.csv")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print("\n", s)
    (RESULTS / f"competition_meta_{stamp}.json").write_text(json.dumps(
        {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "lookback_hours": lookback,
         "assets": args.assets}, indent=2))


if __name__ == "__main__":
    main()
