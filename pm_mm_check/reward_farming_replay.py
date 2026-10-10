"""Replay a liquidity-reward farming bot against the last N days of real Polymarket trades.

For each market in the live liquidity-rewards program (CLOB /rewards/markets/current) the bot is simulated as if it
had been running for the lookback window:

  quoting   every `step` minutes it cancels and re-posts a bid and an ask of S shares around the CLOB mid
            (minute price history), at a distance d from mid: "tight" = 1 tick or "half" = half the max reward spread.
            Optional "pull" rule: skip quoting for 30 min after the mid moves more than 1.5c in one step.
            Inventory is capped at +/- 2*S shares (the side that would grow it is not quoted).
  fills     every real taker trade (Data API) is mapped to the Yes token; a taker sell at a price *below* our bid
            (trade-through, "conservative") or *at or below* it ("optimistic": we are first in the queue) fills our
            bid, and symmetrically for the ask. "adverse" = any trade-through fills our whole remaining size (an
            informed trader would have swept us), the pessimistic bound for thin books.
  rewards   Polymarket's documented score ((v - s) / v)^2 * size per side, two-sided rule with c = 3 inside
            0.10-0.90; our share = our score / (our score + competitors' score), where competitors' score is measured
            from live order-book snapshots taken now and assumed constant over the window.
  P&L       rewards + maker rebate on fills + trading P&L (cash + inventory marked at the final mid, or the payout if
            the market resolved). Fill markouts at +1h and +24h measure adverse selection.

Assumptions to keep in mind: today's reward rate and competing depth are applied to the whole window (rates are
re-issued daily and reward payouts in the window confirm the programs ran); price history is minute mid/last price,
not a full book; our quotes do not change other traders' behaviour.

Usage: python reward_farming_replay.py --days 30 --min-rate 50 --shares 1000
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import pm_api

RESULTS = Path(__file__).parent / "results"
STRATS = {  # name: (distance rule, pull-on-move)
    "tight": ("tick", False),
    "half": ("half", False),
    "half_pull": ("half", True),
}


def reward_markets(min_rate: float) -> list[dict]:
    out, cursor = [], None
    while True:
        d = pm_api.get(f"{pm_api.CLOB}/rewards/markets/current", {"next_cursor": cursor} if cursor else None)
        out.extend(r for r in d.get("data", []) if (r.get("total_daily_rate") or 0) >= min_rate)
        cursor = d.get("next_cursor")
        if not cursor or cursor == "LTE=" or not d.get("data"):
            return out


def gamma_markets(cids: list[str]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(cids), 40):
        batch = cids[i:i + 40]
        for closed in ("false", "true"):
            for m in pm_api.get(f"{pm_api.GAMMA}/markets",
                                [("condition_ids", c) for c in batch] + [("closed", closed), ("limit", 100)]):
                out[m["conditionId"]] = m
    return out


def book_scores(token: str, v: float, min_size: float) -> tuple[float, float] | None:
    """Competitors' reward score (single-market total Qmin approximation) and the book mid."""
    b = pm_api.get(f"{pm_api.CLOB}/book", {"token_id": token})
    bids = [(float(o["price"]), float(o["size"])) for o in b.get("bids", [])]
    asks = [(float(o["price"]), float(o["size"])) for o in b.get("asks", [])]
    qb, qa = [x for x in bids if x[1] >= min_size], [x for x in asks if x[1] >= min_size]
    if not qb or not qa:
        return None
    mid = (max(p for p, _ in qb) + min(p for p, _ in qa)) / 2
    S = lambda s: ((v - s) / v) ** 2 if 0 <= s < v else 0.0
    q1 = sum(S(100 * (mid - p)) * sz for p, sz in qb)
    q2 = sum(S(100 * (p - mid)) * sz for p, sz in qa)
    comp = min(q1, q2) + (max(q1, q2) - min(q1, q2)) / 3 if 0.10 <= mid <= 0.90 else min(q1, q2)
    return comp, mid


def our_qmin(q1: float, q2: float, mid: float) -> float:
    if 0.10 <= mid <= 0.90:
        return max(min(q1, q2), max(q1, q2) / 3)
    return min(q1, q2)


def history(token: str, start: int, end: int) -> tuple[list[int], list[float]]:
    pts = {}
    t = start
    while t < end:
        for h in pm_api.price_history(token, t, min(t + 7 * 86400, end)):
            pts[int(h["t"])] = float(h["p"])
        t += 7 * 86400
    ts = sorted(pts)
    return ts, [pts[x] for x in ts]


def yes_trades(m: dict, start: int) -> tuple[list[dict], bool]:
    rows = pm_api.market_trades(m["conditionId"], taker_only=True)
    truncated = len(rows) >= 10_000
    out = []
    for r in rows:
        ts = int(r["timestamp"])
        if ts < start:
            continue
        p, side = float(r["price"]), r["side"]
        if int(r["outcomeIndex"]) == 1:  # taker buying No = selling Yes at 1 - p
            p, side = 1 - p, ("SELL" if side == "BUY" else "BUY")
        out.append({"ts": ts, "p": p, "side": side, "q": float(r["size"])})
    out.sort(key=lambda x: x["ts"])
    return out, truncated


def simulate(ts, px, trades, *, v, tick, min_size, rate, comp, S, dist, pull, step_s, fill_model, fee_sched,
             payout):
    """Returns P&L components for one market / strategy / fill model."""
    if len(ts) < 10:
        return None
    t0, t1 = max(ts[0], trades[0]["ts"] if trades else ts[0]), ts[-1]
    grid = range(t0 - t0 % step_s + step_s, t1, step_s)
    ti = 0
    cash = inv = rewards = rebates = 0.0
    fills, max_inv, paused_until, prev_mid = [], 0.0, 0, None
    cap = 2 * S
    rr = (fee_sched or {}).get("rebateRate", 0.0)
    rate_fee = (fee_sched or {}).get("rate", 0.0)
    active_steps = 0
    for g in grid:
        i = bisect.bisect_right(ts, g) - 1
        if i < 0:
            continue
        mid = px[i]
        if pull and prev_mid is not None and abs(mid - prev_mid) > 0.015:
            paused_until = g + 1800
        prev_mid = mid
        quoting = g >= paused_until and 0.02 < mid < 0.98
        bid = ask = None
        if quoting:
            d = tick if dist == "tick" else max(tick, round(v / 2 / 100 / tick) * tick)
            bid = math.floor((mid - d) / tick + 1e-9) * tick
            ask = math.ceil((mid + d) / tick - 1e-9) * tick
            if inv >= cap:
                bid = None
            if inv <= -cap:
                ask = None
            # reward score for this step
            sb = ((v - 100 * (mid - bid)) / v) ** 2 * S if bid is not None and 100 * (mid - bid) < v else 0.0
            sa = ((v - 100 * (ask - mid)) / v) ** 2 * S if ask is not None and 100 * (ask - mid) < v else 0.0
            if S >= min_size:
                mine = our_qmin(sb, sa, mid)
                if mine > 0:
                    rewards += rate * step_s / 86400 * mine / (mine + comp)
                    active_steps += 1
        # fills until next requote
        left_b = S if bid is not None else 0.0
        left_a = S if ask is not None else 0.0
        while ti < len(trades) and trades[ti]["ts"] < g + step_s:
            tr = trades[ti]
            ti += 1
            if tr["ts"] < g:
                continue
            optimistic = fill_model == "optimistic"
            if left_b > 0 and tr["side"] == "SELL" and (tr["p"] < bid - 1e-9 or (optimistic and tr["p"] <= bid + 1e-9)):
                q = left_b if fill_model == "adverse" else min(left_b, tr["q"])
                left_b -= q
                cash -= q * bid
                inv += q
                rebates += rr * q * rate_fee * bid * (1 - bid)
                fills.append((tr["ts"], +1, bid, q))
            elif left_a > 0 and tr["side"] == "BUY" and (tr["p"] > ask + 1e-9 or (optimistic and tr["p"] >= ask - 1e-9)):
                q = left_a if fill_model == "adverse" else min(left_a, tr["q"])
                left_a -= q
                cash += q * ask
                inv -= q
                rebates += rr * q * rate_fee * ask * (1 - ask)
                fills.append((tr["ts"], -1, ask, q))
        max_inv = max(max_inv, abs(inv))
    final = payout if payout is not None else px[-1]
    trading = cash + inv * final

    def markout(h):
        tot = 0.0
        for t, sgn, p, q in fills:
            j = bisect.bisect_right(ts, t + h) - 1
            fut = px[j] if t + h <= ts[-1] else final
            tot += sgn * (fut - p) * q
        return tot

    days = (t1 - t0) / 86400
    notional = sum(p * q for _, _, p, q in fills)
    return {"days": days, "fills": len(fills), "filled_notional": notional, "rewards": rewards, "rebates": rebates,
            "trading_pnl": trading, "net": rewards + rebates + trading, "markout_1h": markout(3600),
            "markout_24h": markout(86400), "max_inventory": max_inv, "time_quoting_pct": 100 * active_steps / max(1, len(grid)),
            "capital": S + max_inv}


def run_market(args_tuple):
    r, m, comp, mid_now, start, end, S, step_s = args_tuple
    try:
        token = json.loads(m["clobTokenIds"])[0]
        ts, px = history(token, start, end)
        trades, truncated = yes_trades(m, start)
        if truncated and trades:  # only simulate the window the API still returns
            start = trades[0]["ts"]
            keep = [i for i, t in enumerate(ts) if t >= start]
            ts, px = [ts[i] for i in keep], [px[i] for i in keep]
        payout = None
        if m.get("closed"):
            op = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
            payout = op[0] if sorted(op) == [0.0, 1.0] else None
        v = float(r["rewards_max_spread"])
        base = {"conditionId": m["conditionId"], "question": m["question"][:80], "feeType": m.get("feeType") or "none",
                "rate": r["total_daily_rate"], "v": v, "min_size": r.get("rewards_min_size") or 0, "comp_score": comp,
                "mid_now": mid_now, "trades_truncated": truncated, "n_trades": len(trades),
                "range_c": 100 * (max(px) - min(px)) if px else None,
                "range_first_half_c": None}
        if px:
            half = ts[0] + (ts[-1] - ts[0]) / 2
            fh = [p for t, p in zip(ts, px) if t <= half]
            base["range_first_half_c"] = 100 * (max(fh) - min(fh)) if fh else None
        out = []
        tick = float(m.get("orderPriceMinTickSize") or 0.01)
        sched = m.get("feeSchedule") if m.get("feesEnabled") else None
        for name, (dist, pull) in STRATS.items():
            for fill_model in ("conservative", "optimistic", "adverse"):
                for half_name, (a, b) in {"full": (None, None), "h1": (None, "mid"), "h2": ("mid", None)}.items():
                    if px and half_name != "full":
                        mid_t = ts[0] + (ts[-1] - ts[0]) / 2
                        sel = [i for i, t in enumerate(ts) if (t <= mid_t if half_name == "h1" else t > mid_t)]
                        ts_h, px_h = [ts[i] for i in sel], [px[i] for i in sel]
                        tr_h = [t for t in trades if ts_h and ts_h[0] <= t["ts"] <= ts_h[-1]]
                        pay_h = payout if half_name == "h2" else None
                    else:
                        ts_h, px_h, tr_h, pay_h = ts, px, trades, payout
                    res = simulate(ts_h, px_h, tr_h, v=v, tick=tick, min_size=base["min_size"], rate=base["rate"],
                                   comp=comp, S=S, dist=dist, pull=pull, step_s=step_s, fill_model=fill_model,
                                   fee_sched=sched, payout=pay_h)
                    if res:
                        out.append({**base, "strategy": name, "fill_model": fill_model,
                                    "period": half_name, **res})
        return out
    except Exception as e:
        return [{"conditionId": m.get("conditionId"), "error": repr(e)}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-rate", type=float, default=50)
    ap.add_argument("--shares", type=float, default=1000, help="shares quoted per side")
    ap.add_argument("--step", type=int, default=300, help="re-quote interval, seconds")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-markets", type=int, default=400)
    ap.add_argument("--budget", type=float, default=40000, help="capital budget for the out-of-sample portfolio")
    ap.add_argument("--snap-wait", type=int, default=180, help="seconds between the 3 order-book snapshots")
    args = ap.parse_args()
    now = int(time.time())
    start = now - args.days * 86400
    R = sorted(reward_markets(args.min_rate), key=lambda r: -r["total_daily_rate"])[: args.max_markets]
    G = gamma_markets([r["condition_id"] for r in R])
    print(f"{len(R)} reward markets paying >= ${args.min_rate}/day; {len(G)} with metadata")

    # competitors' score: median of 3 snapshots ~3 minutes apart
    def comp_for(r):
        m = G.get(r["condition_id"])
        if not m:
            return None
        tok = json.loads(m["clobTokenIds"])[0]
        try:
            return book_scores(tok, float(r["rewards_max_spread"]), r.get("rewards_min_size") or 0)
        except Exception:
            return None

    snaps = []
    for k in range(3):
        with ThreadPoolExecutor(args.workers) as ex:
            snaps.append(list(ex.map(comp_for, R)))
        if k < 2:
            time.sleep(args.snap_wait)
    jobs = []
    for i, r in enumerate(R):
        vals = [s[i] for s in snaps if s[i]]
        m = G.get(r["condition_id"])
        if not vals or not m:
            continue
        comp = statistics.median(c for c, _ in vals)
        jobs.append((r, m, comp, vals[-1][1], start, now, args.shares, args.step))
    print(f"simulating {len(jobs)} markets")
    with ThreadPoolExecutor(args.workers) as ex:
        rows = [x for res in ex.map(run_market, jobs) for x in res]
    df = pd.DataFrame(rows)
    errors = df[df.get("error").notna()] if "error" in df else pd.DataFrame()
    df = df[df.get("error").isna()] if "error" in df else df
    print(f"errors: {len(errors)}")
    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d", time.gmtime(now))
    df.to_csv(RESULTS / f"reward_replay_markets_{stamp}.csv", index=False)

    df["apr_net"] = df.net / df.capital * 365 / df.days
    df["apr_rewards"] = df.rewards / df.capital * 365 / df.days
    df["slow"] = df.range_c <= 2 * df.v
    df["slow_ex_ante"] = df.range_first_half_c <= 2 * df.v

    def portfolio(sub):
        days = sub.days.mean()
        cap = sub.capital.sum()
        return pd.Series({
            "markets": len(sub), "avg_days": round(days, 1),
            "fills_per_mkt_day": round((sub.fills / sub.days).mean(), 2),
            "filled_notional_per_mkt_day": round((sub.filled_notional / sub.days).mean(), 1),
            "rewards_per_day": round((sub.rewards / sub.days).sum(), 1),
            "rebates_per_day": round((sub.rebates / sub.days).sum(), 2),
            "trading_pnl_per_day": round((sub.trading_pnl / sub.days).sum(), 1),
            "net_per_day": round((sub.net / sub.days).sum(), 1),
            "capital": round(cap), "portfolio_apr_pct": round(100 * (sub.net / sub.days).sum() * 365 / cap, 1),
            "rewards_apr_pct": round(100 * (sub.rewards / sub.days).sum() * 365 / cap, 1),
            "median_market_apr_pct": round(100 * sub.apr_net.median(), 1),
            "markets_positive_pct": round(100 * (sub.net > 0).mean(), 1),
            "markout_1h_per_day": round((sub.markout_1h / sub.days).sum(), 1),
            "markout_24h_per_day": round((sub.markout_24h / sub.days).sum(), 1),
        })

    full = df[df.period == "full"]
    tables = {}
    tables["all_markets"] = full.groupby(["strategy", "fill_model"]).apply(portfolio)
    tables["slow_vs_fast"] = full.groupby(["strategy", "fill_model", "slow"]).apply(portfolio)
    # out-of-sample: choose markets on the first half (slow + profitable in h1), evaluate on the second half
    h1 = df[df.period == "h1"].set_index(["conditionId", "strategy", "fill_model"])
    h2 = df[df.period == "h2"].set_index(["conditionId", "strategy", "fill_model"])
    pick = h1[(h1.slow_ex_ante) & (h1.net > 0)].index
    oos = h2.loc[h2.index.intersection(pick)].reset_index()
    tables["out_of_sample_picked_on_h1"] = oos.groupby(["strategy", "fill_model"]).apply(portfolio)
    tables["out_of_sample_all_h2"] = h2.reset_index().groupby(["strategy", "fill_model"]).apply(portfolio)
    # $-budgeted portfolio: rank markets by first-half APR, fill a capital budget, evaluate on the second half
    h1r = h1.reset_index()
    h1r["apr_h1"] = h1r.net / h1r.capital / h1r.days
    budget_rows = []
    for (strat, fm), g in h1r.groupby(["strategy", "fill_model"]):
        g = g.sort_values("apr_h1", ascending=False)
        g = g[g.capital.cumsum() <= args.budget]
        sel = h2.loc[h2.index.intersection(list(zip(g.conditionId, g.strategy, g.fill_model)))].reset_index()
        if len(sel):
            budget_rows.append(portfolio(sel).rename((strat, fm)))
    tables[f"out_of_sample_budget_{int(args.budget)}"] = pd.DataFrame(budget_rows)
    for name, t in tables.items():
        t.to_csv(RESULTS / f"reward_replay_{name}_{stamp}.csv")
        with pd.option_context("display.width", 250, "display.max_columns", 30):
            print(f"\n=== {name} ===\n{t}")
    best = full[(full.strategy == "half_pull") & (full.fill_model == "conservative")].sort_values("net", ascending=False)
    best[["question", "feeType", "rate", "v", "comp_score", "days", "fills", "rewards", "trading_pnl", "net",
          "capital", "apr_net", "range_c"]].head(30).round(2).to_csv(RESULTS / f"reward_replay_top_markets_{stamp}.csv",
                                                                    index=False)
    (RESULTS / f"reward_replay_meta_{stamp}.json").write_text(json.dumps({
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "days": args.days,
        "min_rate": args.min_rate, "shares_per_side": args.shares, "requote_seconds": args.step,
        "markets_simulated": int(full.conditionId.nunique()), "errors": len(errors)}, indent=2))


if __name__ == "__main__":
    main()
