"""Robust summary of reward_farming_replay.py output (no new API calls).

- keeps only markets with a long, untruncated window (busy markets hit the Data API's 10k-trade cap and cover only a
  day or two, which makes annualised numbers meaningless)
- classifies markets as slow/fast using the FIRST half of the window only, and reports the SECOND half
- shows how concentrated the rewards are in near-empty books (where a newcomer would take most of the pool)
- builds a capital-budgeted portfolio chosen on the first half, evaluated on the second

Usage: python reward_replay_summary.py --date 20261009 --min-days 20 --budget 40000
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

RESULTS = Path(__file__).parent / "results"


def portfolio(sub: pd.DataFrame) -> pd.Series:
    per_day = lambda c: (sub[c] / sub.days).sum()
    cap = sub.capital.sum()
    return pd.Series({
        "markets": len(sub),
        "days": round(sub.days.mean(), 1),
        "fills_per_market_day": round((sub.fills / sub.days).mean(), 2),
        "rewards_usd_day": round(per_day("rewards"), 1),
        "trading_pnl_usd_day": round(per_day("trading_pnl"), 1),
        "net_usd_day": round(per_day("net"), 1),
        "capital_usd": round(cap),
        "apr_pct": round(100 * per_day("net") * 365 / cap, 1),
        "median_market_apr_pct": round(100 * (sub.net / sub.capital * 365 / sub.days).median(), 1),
        "markets_positive_pct": round(100 * (sub.net > 0).mean(), 1),
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--min-days", type=float, default=20)
    ap.add_argument("--budget", type=float, default=40000)
    args = ap.parse_args()
    d = pd.read_csv(RESULTS / f"reward_replay_markets_{args.date}.csv")
    full = d[d.period == "full"]
    long_ids = set(full[(full.days >= args.min_days) & (~full.trades_truncated)].conditionId)
    d = d[d.conditionId.isin(long_ids)].copy()
    d["slow_ex_ante"] = d.range_first_half_c <= 2 * d.v
    # our reward share (only meaningful as "is the book near-empty?")
    d["pool_share"] = d.rewards / d.days / d.rate
    h1 = d[d.period == "h1"].set_index(["conditionId", "strategy", "fill_model"])
    h2 = d[d.period == "h2"].set_index(["conditionId", "strategy", "fill_model"])
    h2 = h2.join(h1[["net", "capital", "days"]].rename(columns=lambda c: c + "_h1"))
    h2 = h2.reset_index()
    out = {}
    out["h2_by_speed"] = h2.groupby(["strategy", "fill_model", "slow_ex_ante"]).apply(portfolio)
    # exclude near-empty books (we'd take > 50% of the pool) to see the "normal competition" case
    out["h2_by_speed_competitive_only"] = h2[h2.pool_share <= 0.5].groupby(
        ["strategy", "fill_model", "slow_ex_ante"]).apply(portfolio)
    rows = []
    for (s, fm), g in h2.groupby(["strategy", "fill_model"]):
        g = g.assign(apr_h1=g.net_h1 / g.capital_h1 / g.days_h1).sort_values("apr_h1", ascending=False)
        g = g[g.capital.cumsum() <= args.budget]
        rows.append(portfolio(g).rename((s, fm)))
    out[f"h2_budget_{int(args.budget)}_picked_on_h1"] = pd.DataFrame(rows)
    f = d[(d.period == "full") & (d.strategy == "half_pull") & (d.fill_model == "conservative")]
    conc = pd.DataFrame({
        "markets": [len(f)],
        "rewards_usd_day": [round((f.rewards / f.days).sum(), 1)],
        "share_from_near_empty_books_pct": [round(100 * (f[f.pool_share > 0.5].rewards / f[f.pool_share > 0.5].days).sum()
                                                  / (f.rewards / f.days).sum(), 1)],
        "near_empty_books": [int((f.pool_share > 0.5).sum())],
        "median_pool_share_pct": [round(100 * f.pool_share.median(), 2)],
    })
    out["reward_concentration"] = conc
    for name, t in out.items():
        t.to_csv(RESULTS / f"reward_replay_summary_{name}_{args.date}.csv")
        with pd.option_context("display.width", 250, "display.max_columns", 30):
            print(f"\n=== {name} ===\n{t}")


if __name__ == "__main__":
    main()
