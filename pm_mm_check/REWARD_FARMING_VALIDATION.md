# Reward farming: validated with public data

Follow-up to `reports/Polymarket strategies beyond market making.md`. That report left two open questions about its
top-ranked option, liquidity-reward farming. Both can be answered from Polymarket's public APIs. Data was pulled on
2026-10-09/10.

1. **Does the leaderboard P&L already count rewards?** If it did, the "farmers give back about half their rewards"
   finding would be wrong.
2. **How often would a new bot's quotes actually be filled, and at what cost?**

## Bottom line

* **The leaderboard excludes rewards and rebates.** The earlier reading was right.
* **Reward farming is a market-making business, not free yield.** In books with normal competition, the replay gives:
  * **slow markets: roughly 0–15% APR**
  * **active markets: −16% to +87% APR, depending entirely on how fills are modelled**
  * **negative under a worst-case "informed sweep" stress**

  The earlier "10–30% APR" estimate is at the optimistic end of what the data supports for a newcomer.
* **The real money sits in a handful of near-empty books.** In those, a newcomer would collect most of the daily
  pool. In a $40K portfolio this models at several hundred dollars a day. But 5 of those 8 markets lose money once
  informed traders are assumed to sweep the bot's quotes when news hits.
* **Existing farmers are mostly profitable overall but lose heavily on trading.** 32 of 35 reward earners are net
  positive all-time. 20 of 35 lost money on trading, giving back a median 72% of their subsidies.

## 1. Leaderboard P&L excludes rewards (`leaderboard_reward_check.py`)

For 35 reward-earning wallets, I rebuilt all-time P&L from every Data-API activity row:
`sells + redeems + merges − buys − splits + current position value`. I then compared it with the leaderboard's
all-time P&L, both with and without the wallet's `REWARD + MAKER_REBATE + TAKER_REBATE + YIELD` payouts.

| Wallet (example) | Activity rows | Leaderboard | Rebuilt, trading only | Rebuilt, + rewards/rebates |
|---|---:|---:|---:|---:|
| pm-hk | 3,342 | −$18,135 | **−$18,102** | +$14,032 |
| 0xea7f… | 39,397 | −$5,919 | **−$6,921** | +$3,310 |
| 0xc03f… (pogb) | 69,377 | −$53,225 | **−$54,185** | +$2,783 |
| 0x9c18… (rubby1337) | 33,141 | −$11,483 | **−$12,278** | +$4,872 |
| 0x996a… (BunCaCham) | 64,327 | −$177,541 | **−$175,954** | −$51,147 |

* **Most wallets match trading-only.** For 27 of 35 wallets the leaderboard is closer to trading-only P&L than to
  trading + rewards. 19 match trading-only within 10%, and small wallets match within 0.2–2%.
* **The mismatches are data limits.** They are wallets with 100K–1.5M activity rows, where paging and valuing open
  positions at the mid both add error. None of them is consistent with rewards being included.
* **Implication:** a farmer's true result is leaderboard P&L **plus** rewards. The earlier finding that a median 47%
  of rewards is given back used the correct interpretation.

All-time outcome for these 35 earners (`results/leaderboard_reward_check_20261010.json`):

| | Value |
|---|---|
| Net positive (trading + subsidies) | **32 of 35**, median **+$38.8K** all-time |
| Lost money on trading itself | 20 of 35 |
| Median share of subsidies given back (those 20) | **72%** |
| Gave back more than 100% | 3 |
| Total subsidies / total trading P&L (excluding 2 outliers above $1M) | $4.09M / +$0.92M |

These wallets were picked because they are *current* large reward earners, so failed farmers who stopped are missing
(survivorship bias).

## 2. Fill-rate replay (`reward_farming_replay.py`, `reward_replay_summary.py`, `reward_jump_stress.py`)

**Setup.** I replayed a two-sided quoting bot over the last 30 days in the 400 richest reward markets (≥ $50/day):
* 1,000 shares per side, re-quoted every 5 minutes around the CLOB mid
* inventory capped at ±2,000 shares
* reward share computed with Polymarket's documented score against competing depth measured from live order books
* fills taken from every real taker trade

The headline numbers below use only the **113 markets whose full window was available**. Busy markets hit the API's
10,000-trade cap and cover only 1–2 days. Markets are classified as slow or fast using the **first** half of the
window only, and results are measured on the **second** half, out of sample.

**Fill models:**
* **conservative:** filled only when a real trade went through our price
* **optimistic:** also filled at our price, as if first in the queue
* **adverse:** any trade-through fills our whole quote

**Quote placement:**
* **tight:** 1 tick from mid
* **half:** half the max reward spread
* **half_pull:** half spread, plus a 30-minute pause after the mid moves by more than 1.5¢

### Books with normal competition (we would take ≤ 50% of the pool)

| Markets | Quoting | Conservative fills | Optimistic | Adverse | Fills / market-day |
|---|---|---:|---:|---:|---:|
| 32 slow | half_pull | **+4.8% APR** | +10.8% | +12.6% | 0.1–0.5 |
| 32 slow | half | +5.6% | +14.2% | −21.7% | 0.3–1.0 |
| 32 slow | tight | −69.0% | −39.3% | −63.0% | 2–6 |
| 73 active | half_pull | **+84.7%** | +87.3% | −16.0% | 0.4–1.4 |
| 73 active | half | +46.4% | +54.5% | −60.9% | 0.5–2.2 |
| 73 active | tight | −41.5% | −32.1% | −190.5% | 2–8 |

Capital is about $1.5–3K per market: quote collateral plus peak inventory.

* **Slow markets almost never fill, but pay little.** About $1.6/day of reward per market on ~$1.5K of capital, which
  is single-digit to low-teens APR.
* **Active markets pay more, but the result flips with the fill model.** Their sign depends on whether informed flow
  sweeps the full quote (the adverse model). With partial fills they are clearly positive.
* **Quoting at the touch loses in every case.** The reward-score bonus for quoting tight does not cover the extra
  adverse selection.

### Worst-case stress: informed sweep on every jump (`reward_jump_stress.py`)

The stress assumes that each time the mid jumps by more than our quote distance between re-quotes, our losing-side
quote is filled in full and marked at the new mid.

| Group | Markets | Rewards/day | Stress loss/day | Stress APR | Markets positive |
|---|---:|---:|---:|---:|---:|
| Competitive, slow | 32 | $52 | $172 | −46% | 69% |
| Competitive, active | 73 | $379 | $1,434 | −176% | 41% |
| Near-empty books | 8 | $615 | $1,212 | −908% | 38% |

This is a pessimistic bound. Minute price history in thin books includes last-trade bounce, which counts as fake
jumps. The truth lies between this table and the replay table above.

### Near-empty books: where the money is, and the risk

**59.5% of all simulated rewards come from 8 markets** where competing qualifying quotes are almost absent. A newcomer
there would take 58–96% of the daily pool. Examples:
* *Google best text-to-video AI (end Nov)*, $150/day: book 0.37 / 0.74
* *Perim Island under Houthi control by Oct 31*, $200/day
* *Rhine River normal levels*, $100/day
* *UK CPI 3.4–3.6%*, *Fed dissents*, *Mexico GDP* and *SpaceX market cap*: these are event/data-release markets

**$40K portfolio.** Picked on the first half of the window, evaluated on the second, and dominated by these books:
**+$380 to +$900/day** under the three trade-based fill models (half_pull: +$605 to +$851/day).

**The catch is the stress test.** The data-release markets lose $1.3–3.4K each under the sweep test against
$0.5–0.7K of rewards over the same 11–14 days:
* UK inflation: −$3.2K
* SpaceX market cap: −$3.4K
* the two Fed-dissent markets: −$1.3K to −$1.6K each

Only the slow, non-scheduled ones (Google text-to-video, Perim Island, Rhine) stay positive.

**Practical rule:** farm empty books only in markets with no scheduled information event, and pull quotes ahead of any
release.

## What changes in the ranking

Reward farming stays the option with the most capacity, but its expected net for a newcomer should be read as
**"about zero to modestly positive, skill-dependent"**, not a reliable 10–30%.

Its edge comes from three things:
1. finding near-empty books
2. staying out of markets with scheduled releases
3. pulling quotes on moves

That is the same skill as market making elsewhere. The difference from Up/Down rebate market making is that fills are
rare: 0.1–1.5 per market-day at half spread. So the downside comes from occasional large informed sweeps rather than
a steady bleed.

## Caveats

* **Competition is held constant.** Competing depth comes from three book snapshots taken now and is applied to the
  whole past window. Today's reward rates are applied the same way; reward configs are re-issued daily, but payouts in
  the window show the programs ran.
* **Fills ignore unmet demand.** Fills come from trades that actually happened. In thin books an informed trader who
  saw no quote may simply not have traded, which is why the stress test exists.
* **Price history is approximate.** The minute price history is the CLOB's mid/last-trade series, not the full book.
* **Survivorship.** The leaderboard reconstruction covers 35 surviving earners.
