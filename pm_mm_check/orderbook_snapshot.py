"""Live order-book snapshots of the currently trading Up/Down markets: spread, top-of-book size, depth.

Tells you what a new market maker has to beat: how tight the quotes already are and how much size sits at the
best price (queue position behind it).

Usage: python orderbook_snapshot.py --snapshots 6 --every 20
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

import pm_api
from maker_pnl_backtest import INTERVAL_SECONDS

RESULTS = Path(__file__).parent / "results"


def live_markets(assets, intervals, now):
    for iv in intervals:
        step = INTERVAL_SECONDS[iv]
        start = now // step * step
        ev = None
        for a in assets:
            ev = pm_api.event_by_slug(f"{a}-updown-{iv}-{start}")
            if ev and ev.get("markets"):
                m = ev["markets"][0]
                yield a, iv, start + step, m


def book_stats(token_id):
    b = pm_api.get(f"{pm_api.CLOB}/book", {"token_id": token_id})
    bids = sorted(((float(x["price"]), float(x["size"])) for x in b.get("bids", [])), reverse=True)
    asks = sorted((float(x["price"]), float(x["size"])) for x in b.get("asks", []))
    if not bids or not asks:
        return None
    bb, ba = bids[0][0], asks[0][0]
    mid = (bb + ba) / 2

    def depth(side, c):
        return sum(p * s for p, s in side if abs(p - mid) <= c + 1e-9)

    return {"best_bid": bb, "best_ask": ba, "spread_c": round(100 * (ba - bb), 2), "mid": mid,
            "bid_size_top": bids[0][1], "ask_size_top": asks[0][1],
            "depth_usd_1c": depth(bids, .01) + depth(asks, .01), "depth_usd_2c": depth(bids, .02) + depth(asks, .02),
            "depth_usd_5c": depth(bids, .05) + depth(asks, .05), "levels": len(bids) + len(asks),
            "tick": float(b.get("tick_size") or 0), "min_order": float(b.get("min_order_size") or 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="btc,eth,sol,xrp")
    ap.add_argument("--intervals", default="5m,15m,4h")
    ap.add_argument("--snapshots", type=int, default=6)
    ap.add_argument("--every", type=float, default=20)
    args = ap.parse_args()
    rows = []
    for i in range(args.snapshots):
        now = int(time.time())
        for a, iv, end, m in live_markets(args.assets.split(","), args.intervals.split(","), now):
            tok_up = json.loads(m["clobTokenIds"])[0]
            s = book_stats(tok_up)
            if s:
                rows.append({"snapshot": i, "asset": a, "interval": iv, "secs_to_end": end - now, **s})
        if i < args.snapshots - 1:
            time.sleep(args.every)
    df = pd.DataFrame(rows)
    # exclude books near-resolved (mid outside 0.1-0.9): spreads there say little about two-sided quoting
    live = df[(df.mid > 0.1) & (df.mid < 0.9)]
    t = live.groupby(["interval", "asset"]).agg(
        snapshots=("mid", "size"), median_spread_c=("spread_c", "median"), mean_spread_c=("spread_c", "mean"),
        median_top_bid_shares=("bid_size_top", "median"), median_top_ask_shares=("ask_size_top", "median"),
        median_depth_1c_usd=("depth_usd_1c", "median"), median_depth_5c_usd=("depth_usd_5c", "median"),
        tick=("tick", "first"), min_order_shares=("min_order", "first")).round(2)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(t)
    stamp = time.strftime("%Y%m%d", time.gmtime())
    RESULTS.mkdir(exist_ok=True)
    t.to_csv(RESULTS / f"orderbook_summary_{stamp}.csv")
    df.to_csv(RESULTS / f"orderbook_snapshots_{stamp}.csv", index=False)


if __name__ == "__main__":
    main()
