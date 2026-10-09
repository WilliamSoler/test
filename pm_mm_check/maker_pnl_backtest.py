"""Did liquidity providers in Polymarket's short crypto Up/Down markets make money?

For every taker trade in a sample of *resolved* Up/Down markets we compute, from the maker's side:
  spread/adverse-selection P&L  = what the resting order earned against the price later on
      - to resolution (payout 0/1), and as a 1-minute and 5-minute markout against the CLOB price history
  taker fee                     = shares * rate * p * (1 - p)
  maker rebate (pool share)     = rebateRate * taker fee   (the whole pool, split among all makers)

Summing over every fill gives the P&L of the *aggregate* maker population. If makers as a group lose more to
informed takers than the rebate pays back, an average new entrant should expect to lose too.

Usage: python maker_pnl_backtest.py --lookback 15m:72,5m:24,4h:168 --assets btc,eth,sol,xrp
       (lookback = hours of history per market interval)
"""
from __future__ import annotations

import argparse
import bisect
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import pm_api

INTERVAL_SECONDS = {"5m": 300, "15m": 900, "4h": 14400}
RESULTS = Path(__file__).parent / "results"


def windows(assets, lookback, now):
    for iv, hours in lookback.items():
        step = INTERVAL_SECONDS[iv]
        # the slug timestamp is the window start; skip windows that might not be resolved yet
        last = (now - 2 * 3600) // step * step - step
        n = int(hours * 3600 // step)
        for i in range(n):
            for a in assets:
                yield a, iv, f"{a}-updown-{iv}-{last - i * step}", last - i * step


def markout_price(hist_t, hist_p, t, payout0, end):
    """Price of outcome 0 at time t (last print at or before t); after the window ends use the payout."""
    if t >= end:
        return payout0
    i = bisect.bisect_right(hist_t, t) - 1
    return hist_p[i] if i >= 0 else None


def process(win):
    asset, iv, slug, start = win
    try:
        ev = pm_api.event_by_slug(slug, cache=True)
        if not ev or not ev.get("markets"):
            return None
        m = ev["markets"][0]
        if not m.get("closed") or m.get("umaResolutionStatus") not in (None, "resolved"):
            return None
        payouts = [float(x) for x in json.loads(m["outcomePrices"])]
        if sorted(payouts) != [0.0, 1.0]:
            return None
        sched = m.get("feeSchedule") if m.get("feesEnabled") else None
        end = start + INTERVAL_SECONDS[iv]
        trades = pm_api.market_trades(m["conditionId"], taker_only=True, cache=True)
        if not trades:
            return {"slug": slug, "asset": asset, "interval": iv, "trades": []}
        tok0 = json.loads(m["clobTokenIds"])[0]
        t0 = min(t["timestamp"] for t in trades) - 120
        hist = pm_api.price_history(tok0, t0, end + 60, cache=True)
        ht = [h["t"] for h in hist]
        hp = [h["p"] for h in hist]
        rows = []
        for t in trades:
            p, q, idx, ts = float(t["price"]), float(t["size"]), int(t["outcomeIndex"]), int(t["timestamp"])
            sign = 1 if t["side"] == "BUY" else -1  # +1: taker bought, maker sold this token
            payout = payouts[idx]

            def tok_price(px0):
                if px0 is None:
                    return None
                return px0 if idx == 0 else 1 - px0

            mk = {}
            for h in (60, 300):
                px = tok_price(markout_price(ht, hp, ts + h, payouts[0], end))
                mk[h] = None if px is None else sign * (p - px) * q
            f = pm_api.fee(q, p, sched)
            rows.append({
                "slug": slug, "asset": asset, "interval": iv, "ts": ts, "secs_to_end": end - ts,
                "price": p, "shares": q, "notional": p * q, "taker_side": t["side"],
                "fee": f, "rebate": f * (sched or {}).get("rebateRate", 0),
                "maker_pnl_resolution": sign * (p - payout) * q,
                "maker_markout_60s": mk[60], "maker_markout_300s": mk[300],
            })
        return {"slug": slug, "asset": asset, "interval": iv, "trades": rows,
                "gamma_volume": float(m.get("volume") or 0)}
    except Exception as e:  # keep going on individual failures, report them
        return {"slug": slug, "error": repr(e)}


def summarize(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = df.groupby(by, observed=True)
    s = pd.DataFrame({
        "markets": g["slug"].nunique(),
        "trades": g.size(),
        "shares": g["shares"].sum(),
        "notional_usd": g["notional"].sum(),
        "taker_fees_usd": g["fee"].sum(),
        "maker_rebate_pool_usd": g["rebate"].sum(),
        "maker_pnl_to_resolution_usd": g["maker_pnl_resolution"].sum(),
        "maker_markout_60s_usd": g["maker_markout_60s"].sum(),
        "maker_markout_300s_usd": g["maker_markout_300s"].sum(),
    })
    s["fee_pct_of_notional"] = 100 * s["taker_fees_usd"] / s["notional_usd"]
    s["maker_net_resolution_usd"] = s["maker_pnl_to_resolution_usd"] + s["maker_rebate_pool_usd"]
    s["maker_net_bps_of_notional"] = 1e4 * s["maker_net_resolution_usd"] / s["notional_usd"]
    s["rebate_bps_of_notional"] = 1e4 * s["maker_rebate_pool_usd"] / s["notional_usd"]
    s["adverse_sel_bps_resolution"] = 1e4 * s["maker_pnl_to_resolution_usd"] / s["notional_usd"]
    s["adverse_sel_bps_60s"] = 1e4 * s["maker_markout_60s_usd"] / s["notional_usd"]
    s["adverse_sel_bps_300s"] = 1e4 * s["maker_markout_300s_usd"] / s["notional_usd"]
    return s.round(2)


def bootstrap_bps(df: pd.DataFrame, col: str, n: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Point estimate and 95% CI (bps of notional) for column `col`, resampling whole time windows.

    Markets of different coins that share a window are strongly correlated (crypto moves together), so the
    window, not the trade or market, is the independent unit.
    """
    g = df.groupby("window")[[col, "notional"]].sum()
    v, w = g[col].to_numpy(), g["notional"].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(g), size=(n, len(g)))
    boots = 1e4 * v[idx].sum(1) / w[idx].sum(1)
    return 1e4 * v.sum() / w.sum(), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback", default="15m:72,5m:24,4h:168")
    ap.add_argument("--assets", default="btc,eth,sol,xrp")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    now = int(time.time())
    lookback = {k: float(v) for k, v in (x.split(":") for x in args.lookback.split(","))}
    wins = list(windows(args.assets.split(","), lookback, now))
    print(f"{len(wins)} candidate windows")
    with ThreadPoolExecutor(args.workers) as ex:
        res = [r for r in ex.map(process, wins) if r]
    errors = [r for r in res if "error" in r]
    rows = [t for r in res if "trades" in r for t in r["trades"]]
    print(f"markets with data: {sum(1 for r in res if r.get('trades'))}, errors: {len(errors)}")
    for e in errors[:5]:
        print("  ", e)
    df = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    df["price_bucket"] = pd.cut(df["price"], [0, .05, .2, .4, .6, .8, .95, 1.0])
    df["time_left"] = pd.cut(df["secs_to_end"], [-1e9, 60, 180, 600, 3600, 1e9],
                             labels=["<1m", "1-3m", "3-10m", "10-60m", ">60m"])
    tables = {
        "by_interval": summarize(df, ["interval"]),
        "by_interval_asset": summarize(df, ["interval", "asset"]),
        "by_price_bucket": summarize(df, ["interval", "price_bucket"]),
        "by_time_left": summarize(df, ["interval", "time_left"]),
    }
    # aggregate across all intervals
    df["all"] = "ALL"
    tables["total"] = summarize(df, ["all"])
    stamp = time.strftime("%Y%m%d", time.gmtime(now))

    df["window"] = df["interval"] + "-" + df["slug"].str.rsplit("-", n=1).str[1]
    df["maker_net"] = df["maker_pnl_resolution"] + df["rebate"]
    df["maker_net_60s"] = df["maker_markout_60s"].fillna(0) + df["rebate"]
    df["maker_net_300s"] = df["maker_markout_300s"].fillna(0) + df["rebate"]
    ci_rows = []
    for name, sub in [("ALL", df)] + list(df.groupby("interval")) + list(df.groupby(["interval", "asset"])):
        for col in ("rebate", "maker_pnl_resolution", "maker_net", "maker_net_60s", "maker_net_300s"):
            est, lo, hi = bootstrap_bps(sub, col)
            ci_rows.append({"subset": name if isinstance(name, str) else "/".join(name), "metric": col,
                            "bps_of_notional": round(est, 1), "ci95_lo": round(lo, 1), "ci95_hi": round(hi, 1)})
    ci = pd.DataFrame(ci_rows)
    ci.to_csv(RESULTS / f"maker_pnl_ci_{stamp}.csv", index=False)
    print("\n=== 95% CIs (window-clustered bootstrap) ===")
    print(ci.to_string(index=False))
    per_market = df.groupby(["interval", "asset", "slug"]).agg(
        trades=("ts", "size"), notional=("notional", "sum"), fees=("fee", "sum"), rebate=("rebate", "sum"),
        maker_pnl_resolution=("maker_pnl_resolution", "sum")).round(4)
    per_market.to_csv(RESULTS / f"maker_pnl_per_market_{stamp}.csv")
    for name, t in tables.items():
        t.to_csv(RESULTS / f"maker_pnl_{name}_{stamp}.csv")
        with pd.option_context("display.width", 250, "display.max_columns", 30):
            print(f"\n=== {name} ===\n{t}")
    meta = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "lookback_hours": lookback, "assets": args.assets, "first_trade_ts": int(df.ts.min()),
            "last_trade_ts": int(df.ts.max()), "markets": int(df.slug.nunique()), "trades": len(df)}
    (RESULTS / f"maker_pnl_meta_{stamp}.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
