"""Worst-case "informed sweep" stress for the reward-farming replay.

In a thin book an informed trader who learns news first takes whatever quote is resting, so trade-based fill models
understate losses there. This stress assumes that every time the mid jumps by more than our quote distance between two
re-quotes, our quote on the losing side is filled in full and marked at the new mid:
    loss = S * (|jump| - d)
With the "pull" rule only the first jump in each 30-minute pause is charged. The result is set against the rewards
from the replay (second half of the window, half-spread quotes with pull).

Usage: python reward_jump_stress.py --date 20261010 --min-days 20
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

import pm_api
from reward_farming_replay import history

RESULTS = Path(__file__).parent / "results"


def jump_loss(ts, px, S, d, step_s=300, pause_s=1800):
    loss, paused_until, prev = 0.0, 0, None
    import bisect
    for g in range(ts[0] - ts[0] % step_s + step_s, ts[-1], step_s):
        mid = px[bisect.bisect_right(ts, g) - 1]
        if prev is not None and g >= paused_until:
            j = abs(mid - prev)
            if j > d:
                loss += S * (j - d)
                paused_until = g + pause_s
        prev = mid
    return loss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--min-days", type=float, default=20)
    ap.add_argument("--shares", type=float, default=1000)
    args = ap.parse_args()
    d = pd.read_csv(RESULTS / f"reward_replay_markets_{args.date}.csv")
    full = d[(d.period == "full") & (d.strategy == "half_pull") & (d.fill_model == "conservative")]
    full = full[(full.days >= args.min_days) & (~full.trades_truncated)]
    h2 = d[(d.period == "h2") & (d.strategy == "half_pull") & (d.fill_model == "conservative")].set_index("conditionId")
    h1 = d[(d.period == "h1") & (d.strategy == "half_pull") & (d.fill_model == "conservative")].set_index("conditionId")
    G = {}
    ids = list(full.conditionId)
    for i in range(0, len(ids), 40):
        for closed in ("false", "true"):
            for m in pm_api.get(f"{pm_api.GAMMA}/markets", [("condition_ids", c) for c in ids[i:i + 40]]
                                + [("closed", closed), ("limit", 100)]):
                G[m["conditionId"]] = m

    def one(row):
        m = G.get(row.conditionId)
        if not m or row.conditionId not in h2.index:
            return None
        tok = json.loads(m["clobTokenIds"])[0]
        end = int(pd.Timestamp.now(tz="UTC").timestamp())
        ts, px = history(tok, end - 30 * 86400, end)
        if len(ts) < 20:
            return None
        mid_t = ts[0] + (ts[-1] - ts[0]) / 2
        sel = [(t, p) for t, p in zip(ts, px) if t > mid_t]
        tick = float(m.get("orderPriceMinTickSize") or 0.01)
        dist = max(tick, round(row.v / 2 / 100 / tick) * tick)
        loss = jump_loss([t for t, _ in sel], [p for _, p in sel], args.shares, dist)
        r = h2.loc[row.conditionId]
        return {"conditionId": row.conditionId, "question": row.question, "rate": row.rate,
                "pool_share": r.rewards / r.days / row.rate, "slow_ex_ante": h1.loc[row.conditionId].range_first_half_c
                <= 2 * row.v if row.conditionId in h1.index else None,
                "days": r.days, "rewards": r.rewards, "jump_loss": loss, "capital": args.shares * 3,
                "net_stress": r.rewards - loss}

    with ThreadPoolExecutor(8) as ex:
        rows = [x for x in ex.map(one, full.itertuples()) if x]
    df = pd.DataFrame(rows)
    df["near_empty_book"] = df.pool_share > 0.5
    df.to_csv(RESULTS / f"reward_jump_stress_markets_{args.date}.csv", index=False)
    g = df.groupby(["near_empty_book", "slow_ex_ante"])
    t = pd.DataFrame({
        "markets": g.size(),
        "rewards_usd_day": g.apply(lambda s: (s.rewards / s.days).sum()).round(1),
        "jump_loss_usd_day": g.apply(lambda s: (s.jump_loss / s.days).sum()).round(1),
        "net_stress_usd_day": g.apply(lambda s: (s.net_stress / s.days).sum()).round(1),
        "apr_stress_pct": g.apply(lambda s: 100 * (s.net_stress / s.days).sum() * 365 / s.capital.sum()).round(1),
        "markets_positive_pct": g.apply(lambda s: 100 * (s.net_stress > 0).mean()).round(1),
    })
    t.to_csv(RESULTS / f"reward_jump_stress_summary_{args.date}.csv")
    print(t)
    print(df[df.near_empty_book][["question", "rate", "pool_share", "rewards", "jump_loss", "net_stress", "days"]]
          .round(2).to_string(index=False))


if __name__ == "__main__":
    main()
