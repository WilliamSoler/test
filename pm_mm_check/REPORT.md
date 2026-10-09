# Polymarket market making: feasibility & profitability check

Data pulled from Polymarket's **public, no-auth APIs** (Gamma, Data-API, CLOB) on **2026-10-09**.
Every number below is reproducible with the scripts in this folder (see `README.md`); raw outputs are in `results/`.

## Bottom line

**Feasible: yes. Profitable: only for the best ~200 makers. The rebate alone is not an edge.**

* The fee mechanics described are **correct** (rate 0.07 inside `shares × rate × p × (1−p)`, takers only, 20% rebated
  to makers in crypto, paid daily pro-rata per market).
* Across 5,328 resolved BTC/ETH/SOL/XRP Up/Down markets ($32M traded), the maker rebate was worth **0.42%** of
  filled notional. Losses to better-informed takers cost makers about the same, **0.50%**. **Makers as a group netted
  −0.09%** (95% CI −0.83% … +0.68%), so roughly break-even.
* The money is concentrated. Over 48h, the **top 50 maker wallets earned +1.3%** on their fills (≈ $1,000/day each),
  ranks 51–200 earned +0.8%, and **the other ~4,900 maker wallets lost money** (−0.9% to −4.5%).
* The crypto-market rebate pool that this strategy can reach is about **$14–17M/yr**. The all-category pool is about
  **$40–70M/yr**. That sits inside the claimed $25–250M range, but near the bottom of it.

A new $10–50K operator starts in the losing tier. To make money they need to price faster and better than ~5,000 other
makers, many of them already automated. Realistic outcomes span from losing money, to about $60K/yr (rank ~51–200), to
about $300K/yr (top 50).

## Claim-by-claim

| Claim | Verdict | Evidence (public API) |
|---|---|---|
| Taker fee = shares × rate × p × (1−p) | ✅ Confirmed | Every market carries `feeSchedule {rate, exponent:1, takerOnly:true, rebateRate}` in Gamma; CLOB `/fee-rate` agrees |
| Crypto: $1.75 per 100 shares at $0.50 = 3.5% | ✅ Confirmed | `crypto_fees_v2`: rate 0.07 → 100×0.07×0.25 = $1.75 = 3.50% of $50 (`claims_check.py`) |
| …so takers pay ~3.5% | ⚠️ Only at p = 0.5 | Fee as % of money paid is `rate×(1−p)`: 6.3% at $0.10, 0.7% at $0.90. **Realised average in Up/Down markets: 2.08%** of notional |
| 15–25% of fees rebated daily, pro-rata to filled volume | ✅ Mostly | Crypto 20%, sports 15%, most others 25% (`rebateRate` field + docs). The pro-rata weight is *fee-equivalent* (C×rate×p(1−p)), per market, so fills near $0.01/$0.99 earn almost nothing |
| 0.03–0.07 is a rate inside the formula | ✅ Confirmed | Live rates: crypto 0.07, sports 0.05 / 0.03, politics/finance/tech/mentions 0.04, culture/econ/weather 0.05, geopolitics 0 |
| Edge moved from takers to makers | ⚠️ Partly | Takers pay 2.1% in fees + ~1¢ spread, but the maker side **as a whole** only breaks even after rebates. The edge went to the *best* makers |
| Rebate pool ≈ $25–250M/yr | ⚠️ Low end | Measured taker fees ≈ $0.6–1.2M/day → **rebate pool ≈ $43–71M/yr all categories**. Crypto ≈ $14–17M/yr. Sports is the biggest pool (≈ $47M/yr) |
| Competing against faster, informed traders | ✅ Confirmed | Maker fills are +0.65% after 60s but −0.14% after 5 min: takers' information shows up within minutes |
| Pro MMs compete for the same rebates | ✅ (but fragmented) | 5,110 maker wallets in 48h; top 10 = 18% of maker volume (HHI 68). Profits sit with the top ~200 |
| Polymarket changes rules often | ✅ Confirmed | 16 fee schedules live at once: `crypto_fees` (0.25), `crypto_15_min` (0.25), `crypto_fees_v2` (0.07), `sports_fees_v2` (0.03/25%), `sports_fees_v3` (0.05/15%), `sports_fees_nfl_cfb_oct26` (0.03/15%), … |
| $10–50K capital needed | ✅ Plausible | Min order 5 shares, tick $0.01. A rank-11–50 maker fills ≈ $72K/day in markets that settle every 5–15 min, so capital recycles many times a day |
| Check if Polymarket is open where you live | ⚠️ Must check yourself | `polymarket.com/api/geoblock` returned `blocked: true` for this US (OH) cloud server. Run `claims_check.py` from your own connection |
| Kalshi incentive details | ➖ Not checked | Outside Polymarket's API |

## 1. Fee and rebate pool size (`fee_census.py`)

Coverage: every active market (279,228) plus every market that closed in the last 24h (76,874), each with its fee
schedule and 24h volume. A 10.9-minute sample of 6,814 platform-wide taker trades was priced exactly with each market's
schedule.

| Fee type | 24h volume (shares) | Taker fees 24h | Rebate pool 24h | Rebate pool /yr |
|---|---:|---:|---:|---:|
| sports_fees_v3 (0.05 / 15%) | 82.8M | $799K | $120K | $43.8M |
| crypto_fees_v2 (0.07 / 20%) | 22.9M | $236K | $47K | $17.2M |
| sports_fees_nfl_cfb_oct26 (0.03 / 15%) | 9.4M | $66K | $10K | $3.6M |
| politics_fees (0.04 / 25%) | 7.0M | $30K | $7K | $2.7M |
| everything else | 18.3M | $38K | $10K | $3.5M |
| **Total** | **140M** | **$1.17M** | **$194K** | **$71M** |

* Cross-check from the 10.9-min trade sample, annualised: **$214M fees / $43M rebates per year**. The Gamma-volume
  method gives $427M / $71M. Both are single-day snapshots (a Friday).
* The crypto Up/Down backtest below measures ≈ $40K/day of rebates for BTC/ETH/SOL/XRP 5m+15m+4h. That is
  **≈ $14M/yr**, consistent with the $17M/yr for all crypto.
* The separate **liquidity-rewards** program (`clobRewards`) lists ≈ $200K/day across markets. Only $4.5K/day of that
  is on crypto markets, and **none is on the Up/Down markets**.
* Gamma's `volume`/`volume24hr` count **shares**, not dollars. They matched the summed trade sizes exactly.

## 2. Did makers make money? (`maker_pnl_backtest.py`)

The sample is every BTC/ETH/SOL/XRP Up/Down market that resolved in the lookback: 15-minute markets over 7 days,
5-minute over 2 days, and 4-hour over 14 days. That is **5,328 markets, 2.22M taker trades, $32.1M notional**, with
trades from Sep 24 to Oct 9, 2026.

Each taker fill is seen from the maker side. The P&L is computed to resolution and as 60s/300s markouts against CLOB
minute prices. The rebate is 20% of the fill's fee. The 95% CIs come from a bootstrap that resamples whole time windows,
because coins in the same window move together.

| Subset | Notional | Taker fee % | Rebate | Maker P&L to resolution | **Maker net** (95% CI) | Net, 60s markout | Net, 5-min markout |
|---|---:|---:|---:|---:|---:|---:|---:|
| **All** | $32.1M | 2.08% | +0.42% | −0.50% | **−0.09%** (−0.83 … +0.68) | +0.65% | −0.14% |
| 5-minute | $15.0M | 1.94% | +0.39% | +0.27% | **+0.66%** (+0.10 … +1.22) | +0.71% | +0.65% |
| 15-minute | $16.1M | 2.21% | +0.44% | −1.28% | **−0.84%** (−2.24 … +0.54) | +0.50% | −0.98% |
| 4-hour | $1.1M | 2.31% | +0.46% | +0.19% | **+0.66%** (−1.12 … +2.30) | +1.98% | +1.21% |

What this says:

* **Rebate ≈ adverse selection.** The rebate is a reliable +0.4% (tight CI). Price moves against the maker are just as
  large and much noisier. On average, a maker that only collects rebates does not make money.
* **Makers win the first minute and lose the next four** (60s net +0.65% → 5-min net −0.14%). Takers carry real
  short-horizon information, presumably the spot price on Binance/Coinbase. A maker therefore has to re-price and
  cancel within seconds and flatten or hedge inventory, rather than sit on the book.
* **Fees disappear near expiry.** In the last minute, takers pay only 0.9% (prices are near 0 or 1), so the rebate is
  ~0.2%. Meanwhile makers lost 2.2% on 15-minute markets in that last minute. Quoting into the close is where makers
  get picked off.
* By market: BTC 15-minute makers lost (−1.2% net). ETH/SOL/XRP 15-minute and all 5-minute markets were positive, but
  most CIs include zero. Per-asset and per-price tables are in `results/maker_pnl_by_*.csv`.

## 3. Who captures it? (`competition.py`)

Sample: 48h (Oct 7–9) of all 5m/15m/4h BTC/ETH/SOL/XRP Up/Down markets. That is 3,120 markets, **5,110 maker wallets**,
and $20.1M of maker fills (≈ $10M/day). Every maker leg is attributed to its wallet. Rebates are estimated with
Polymarket's per-market fee-equivalent rule.

| Maker rank (by volume) | Wallets | Share of maker volume | Net (P&L + rebate) | Net % of fills | Profitable | ≈ Net per wallet per day |
|---|---:|---:|---:|---:|---:|---:|
| 1–10 | 10 | 17.8% | +$28.4K | **+0.80%** | 90% | ~$1,400 |
| 11–50 | 40 | 28.6% | +$74.9K | **+1.30%** | 85% | ~$940 |
| 51–200 | 150 | 33.4% | +$51.0K | **+0.76%** | 81% | ~$170 |
| 201–1000 | 800 | 17.8% | −$33.4K | **−0.93%** | 46% | −$21 |
| >1000 | 4,110 | 2.3% | −$21.2K | **−4.51%** | 34% | −$3 |

* **The market is fragmented, not dominated by one firm.** The largest wallet has 3.5% of maker volume and the top 10
  have 18% (HHI 68). One firm can run several wallets, so true concentration is higher.
* **The #1 maker by volume is close to a pure rebate farm.** It filled ≈ $355K/day and netted ≈ $1.4K/day. Its
  resolution P&L was about zero, so all of its profit is rebate, roughly $500K/yr if sustained. That shows the strategy
  in its best case, at a scale a $10–50K account will not reach soon.
* **The top 200 earn more from P&L than from rebates** (≈ $96K vs ≈ $58K over 48h). Their pricing edge matters
  more than the subsidy. Ranks 201+ lose money even with the rebate.

## 4. What you'd be quoting against (`orderbook_snapshot.py`)

Live books, 8 snapshots ~20s apart, counting only books with a mid between 0.1 and 0.9:

| Market | Median spread | Depth within 1¢ of mid | Depth within 5¢ |
|---|---:|---:|---:|
| BTC 15m | 1¢ (1 tick) | ~$1,570 | ~$16,550 |
| BTC 5m | 1¢ | ~$1,230 | ~$4,610 |
| ETH 15m / 5m | 1¢ | ~$155–215 | ~$1.6–3.2K |
| SOL, XRP 15m / 5m | 1–1.5¢ | ~$50–85 | ~$0.3–1.1K |
| BTC/ETH/SOL 4h | 3–5¢ | ~0 | ~$0.4–1.9K |

The BTC books already sit at the minimum tick, with a queue in front of you. ETH/SOL/XRP and the 4-hour markets have
wider, thinner books, so there is less competition there, but they carry 10–35× less volume (ETH 15m ≈ $190K/day vs BTC 15m ≈ $2.0M/day).

## What would make it work, and what wouldn't

* **Won't work:** posting both sides around the mid and waiting for rebates. That is the 201+ tier, which loses
  0.9–4.5%.
* **Needed to reach the top 200:**
  * a fair-value model driven by a fast spot feed from Binance/Coinbase
  * cancel and re-quote within seconds
  * pulling quotes in the final 1–3 minutes
  * skewing quotes or hedging to keep inventory flat
  * favouring the 5-minute markets and the less crowded ETH/SOL books
* **Next validation step:** paper-trade the quoting logic against the recorded books and trades before risking
  capital. These scripts give the baseline it has to beat: about +0.4% rebate against about −0.5% adverse selection.

## Caveats

* **Short sample.** Two weeks of backtest, 48h of wallet data, one day of Gamma volume and a 10-minute trade snapshot.
  Results depend on how volatile crypto is.
* **No hedges counted.** Wallet P&L is Polymarket-only and held to resolution. It ignores hedges on other venues and
  ignores the same firm running several wallets.
* **Rebates are estimates.** They are computed from the documented formula. Actual payouts are not in the public API;
  they could be checked from on-chain pUSD transfers.
* **API limits.** The Data-API caps history at 10,000 rows per query. 19 of 3,120 markets (0.6%) were truncated in the
  wallet study.
* **Approximate markouts.** The 60s/5-min markouts use CLOB `prices-history` minute points.
* **Geoblock is for this server only.** The geoblock result applies to this cloud server's IP, not to you. Polymarket's
  terms forbid getting around the block with a VPN.
