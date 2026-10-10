"""Does Polymarket's leaderboard P&L include liquidity rewards and maker rebates?

Rebuilds each wallet's all-time P&L from its Data-API activity cash flows:
    trading P&L = sells + redeems + merges + conversions - buys - splits + current position value
    subsidies   = REWARD + MAKER_REBATE + TAKER_REBATE + YIELD (holding rewards)
and compares both "trading only" and "trading + subsidies" with the leaderboard's all-time P&L.

Usage: python leaderboard_reward_check.py 0xWALLET [0xWALLET ...]
"""
import sys, json, collections
from pm_api import get
D = "https://data-api.polymarket.com"

def all_acts(w):
    out, end, seen = [], None, set()
    while True:
        p = {"user": w, "limit": 500, "sortBy": "TIMESTAMP", "sortDirection": "DESC"}
        if end: p["end"] = end
        page = get(f"{D}/activity", p)
        new = [a for a in page if (a["transactionHash"], a["type"], a.get("asset"), a["usdcSize"], a["side"]) not in seen]
        for a in new: seen.add((a["transactionHash"], a["type"], a.get("asset"), a["usdcSize"], a["side"]))
        out += new
        if len(page) < 500 or not new: break
        end = page[-1]["timestamp"]  # inclusive; dedupe handles overlap
    return out

def recon(w):
    A = all_acts(w)
    flows = collections.Counter()
    for a in A:
        t, u = a["type"], a["usdcSize"]
        if t == "TRADE": flows["BUY" if a["side"] == "BUY" else "SELL"] += u
        else: flows[t] += u
    val = get(f"{D}/value", {"user": w})
    val = val[0]["value"] if val else 0.0
    trade = flows["SELL"] + flows["REDEEM"] + flows["MERGE"] + flows["CONVERSION"] - flows["BUY"] - flows["SPLIT"] + val
    subsidy = flows["REWARD"] + flows["MAKER_REBATE"] + flows.get("YIELD", 0) + flows.get("TAKER_REBATE", 0)
    lb = get(f"{D}/v1/leaderboard", {"timePeriod": "ALL", "orderBy": "PNL", "user": w})
    lb = lb[0]["pnl"] if lb else None
    up = get("https://user-pnl-api.polymarket.com/user-pnl", {"user_address": w, "interval": "all", "fidelity": "1d"})
    up = up[-1]["p"] if up else None
    return {"wallet": w, "n_acts": len(A), "types": dict(flows), "pos_value": val, "trading_pnl": trade,
            "subsidies": subsidy, "trading_plus_subsidies": trade + subsidy, "leaderboard": lb, "profile_chart": up}

if __name__ == "__main__":
    for w in sys.argv[1:]:
        r = recon(w)
        print(json.dumps({k: (round(v) if isinstance(v, float) else v) for k, v in r.items() if k != "types"}),
              {k: round(v) for k, v in r["types"].items()})
