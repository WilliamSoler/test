# Arbitrage on Polymarket after the 2026 taker fees (as of 9 Oct 2026)

Method note. All "live" numbers come from read-only Polymarket, Kalshi and Deribit public APIs, pulled on **2026-10-09 between 22:33 and 22:54 UTC** (a Friday evening, US time).
- **Events covered:** every open Polymarket event, 22,877 of them, holding 277,387 live markets. They were paged with Gamma `/events/keyset?closed=false`.
- **Order books:** full-depth CLOB books for about 278K tokens, pulled in 36–40 s per sweep with `POST https://clob.polymarket.com/books` (500 tokens per call). The sweep covered the YES token of every market in every multi-market event, plus both tokens of a random sample of 4,000 single-market events. Four sweeps were taken at 22:42, 22:46, 22:50 and 22:54 UTC.
- **Fees:** each market's own `feeSchedule` was applied: fee = shares × rate × p × (1−p), with exponent 1.
- **Scripts and CSVs:** they sit in `/tmp/claude-0/-home-user-test/0ced0027-bcc3-524f-9ed3-ebcec6816192/scratchpad/arb/`: `dump_events.py`, `fetch_books.py`, `analyze_negrisk.py`, `analyze_ladders.py`, `crypto_xcheck.py`, `kalshi_fed.py` and `kalshi_btc.py`. Outputs are `negrisk_scan_[0-3].csv`, `ladder_viol_[0-3].csv`, `crypto_vs_deribit.csv` and `crypto_range_vs_above.csv`.
- **Limits:** these are snapshots. They cannot see opportunities that open and close in under a second, so frequency evidence for fleeting arbitrage comes from the literature (below).

## Q1. Intra-Polymarket arbitrage: binary YES+NO, negative-risk (multi-outcome) sums, and logically linked markets (ladders, nested dates)

### Takeaway
At this snapshot there is essentially no fee-surviving, riskless intra-Polymarket arbitrage left.
- **Binary YES+NO:** structurally impossible, because the CLOB mirrors the YES and NO books.
- **Buy-all-YES:** across 7,788 complete negRisk events, about $1 of genuine profit was available at full depth. The other "opportunities" were augmented or placeholder events that do not cover every outcome, and buying all their YES legs is not riskless.
- **Buy-all-NO:** zero opportunities survived fees.
- **Ladders and nested dates:** about $0.50 of extractable edge across 748 events.

The 2026 taker fee adds a hurdle of roughly rate × (1 − Σp²), which is about 2.5–4.5¢ per $1 basket. Gross mispricings almost never exceed it. What remains is sub-second, a few shares deep, and taken by bots.

### Cited Findings

**Live-data results (Polymarket APIs, 2026-10-09)**

*Binary YES+NO*
- In 3,976 sampled binary markets with both books, no market had YES ask + NO ask < 1 (minimum 1.001, median 1.0155) and none had YES bid + NO bid > 1 (maximum 0.999). In 3,436 of them the NO best ask equals exactly 1 − YES best bid. The books are mirrored: complementary orders are matched against each other by minting or merging, so binary "rebalancing" arbitrage cannot appear in the visible book. — [Polymarket CLOB `/books` API](https://clob.polymarket.com/books), own computation.

*Size of the universe*
- 10,297 open events are negRisk: 7,840 plain and 2,457 "augmented". Together they hold 103,534 live outcome markets. 5,531 of these events have exactly 3 outcomes (mostly soccer win/draw/win) and 1,741 have 20 or more. — [Gamma events API](https://gamma-api.polymarket.com/events/keyset), own computation.

*Buy-all-YES (sum of best YES asks < 1), first sweep*
- 224 negRisk events had a gross sum of asks below 1, 159 were still positive after fees, and the depth-aware profit summed to $7,656 on $82K of cost. Almost all of this comes from augmented events, where the listed outcomes are not exhaustive and the "Other" or placeholder markets are not tradable. Examples: Republican Nominee 2028 (43 listed outcomes, sum of asks 0.854, 760 days to resolution) and Presidential Election Winner 2028 (sum 0.923). Buying every listed YES is a directional bet against an unlisted winner, not an arbitrage. — Gamma `negRiskAugmented` flag plus CLOB books, own computation; [Polymarket negative-risk docs](https://docs.polymarket.com/developers/neg-risk/overview) say to "trade only on named outcomes" and that "Other" changes definition as placeholders are named.
- Restricted to the 7,788 non-augmented events (all of them complete), 12 had gross sum of asks < 1 and 5–6 were positive after fees (5 in the first sweep, 6 in the next three). Depth-aware profit was **$33.4–33.7 in each of the four sweeps**, on about $386 of capital.
  - $33 of that came from two Guinea-Bissau 2025 election events, both past their end date. Their placeholder and "Other" markets are not tradable, and the rules resolve to "Other" if no result is known by 31 Dec 2026. So they are not riskless either. — [Gamma event `guinea-bissau-presidential-election`](https://gamma-api.polymarket.com/events?slug=guinea-bissau-presidential-election)
  - The genuinely riskless remainder was about $1:
    - ECB October decision: sum of asks 0.993, 148 sets, $0.25 profit.
    - "Democratic House incumbents not winning primary": 2 remaining live buckets summing to 0.985, 55 sets, $0.46.
    - OpenAI IPO closing market cap: $0.01.
    - Hormuz traffic (fee-free geopolitics): $0.03.
- Distribution of the sum of best YES asks over the 7,788 complete events:

  | Sum of best YES asks | Events |
  |---|---:|
  | below 1.00 | 12 |
  | 1.000–1.005 | 51 |
  | 1.005–1.01 | 14 |
  | 1.01–1.02 | 137 |
  | 1.02–1.05 | 1,105 |
  | 1.05–1.2 | 1,152 |
  | above 1.2 (thin long tails) | 5,317 |

  Active 3-outcome events (24h volume > 1,000 shares) have a median sum of asks of 1.020 and a median sum of bids of 0.990. — own computation.

*Buy-all-NO (sum of best YES bids > 1)*
- This trade is riskless even in augmented events: buying NO on k listed outcomes pays at least k−1. In the first sweep 26 negRisk events had sum of bids > 1 (24–25 in later sweeps). The largest gross edges were Worlds 2026 winner at 1.028, AFCON qualifying group F at 1.019 and NHL 2027 champion at 1.018. **None was positive after fees**: net edges ranged from −0.2¢ to −4.1¢. The NO-leg fees on a 30-outcome basket add up to roughly rate × Σb, which is about 3–5¢. — own computation.

*Fee hurdle*
- For buying a complete basket at top of book, the fee drag was a median of 2.6¢ for 3-outcome events, 2.5¢ for 4–5 outcomes and 3.7¢ for 6–20 outcomes. This follows from fee = rate × Σ p_i(1−p_i) = rate × (1 − Σp_i²). — own computation; fee formula and rates from [Polymarket fee docs](https://docs.polymarket.com/polymarket-learn/trading/fees).
- Of the 7,788 complete negRisk events, 7,339 are at rate 0.05 (sports, weather and similar), 230 at 0.04, 161 at 0.03, 39 at 0.07 and 19 fee-free. — own computation.

*Ladders and nested dates*
- 748 non-negRisk ladder or nested events were checked for monotonicity. They include "BTC/ETH/SOL/XRP above ___ on Oct X", "What price will X hit", "Fed rate hit before 2027", FX "hit" ladders, valuation ladders, "by date" cumulative events and "continues through" survival events. Each sweep found only 7–8 violating pairs that survived fees, worth **$0.46–0.52 in total**. Examples:
  - Fed lower bound "≤0.5% before 2027" bid 0.021 vs "≤1.75%" ask 0.016, 56 shares.
  - USD/JPY 110-low vs 120-low, 13 shares.
  - Kraken valuation $22.5B vs $20B, 5 shares.
- An earlier version of the parser produced large false positives. It misread "ceasefire continues through …" as cumulative "by date", and month-only labels such as "March 31" as past dates. Any automated logical-arbitrage scanner faces the same semantic risk. — own computation.

*Range buckets vs "above" ladders*
- For BTC and ETH, October 10–16, the negRisk "price on Oct X" range buckets were combined with the "above ___ on Oct X" ladder. Two synthetic $1 payoffs were tested: YES above K plus YES on every bucket below K; and NO above K plus YES on every bucket from K up. Across 140 strike–date combinations, the cheapest cost was 1.001 gross and 1.0011 after fees. Median cost was 1.12 for the first payoff and 1.11 for the second, gross. **No combinatorial arbitrage was found.** — own computation.

**Literature**
- *Saguillo, Ghafouri, Kiffer & Suarez-Tangil, "Unravelling the Probabilistic Forest" (arXiv 2508.03474; AFT 2025):*
  - **Data and scope:** Polymarket markets resolved 1 Apr 2024 – 1 Apr 2025, covering 17,218 conditions (8,659 single-condition markets and 1,578 NegRisk markets).
  - **Headline total:** $39,587,585 "extracted" across all strategies.
  - **NegRisk split:** buy-YES $11.09M, buy-NO $17.31M, sell-YES $0.61M. Single-condition: buy below $1 $5.90M, sell above $1 $4.68M.
  - **Combinatorial:** only about $95K across 4 dependent pairs, with an average maximum profit of about $100.
  - **Concentration:** the top account made $2.01M over 4,049 transactions.
  - **Caveats in the paper:** fees were excluded ("Polymarket currently does not charge per trade executed"), trades were non-atomic, and bids within 950 blocks (about 1 hour) were grouped as one opportunity. — [arXiv HTML](https://arxiv.org/html/2508.03474); [arXiv abstract](https://arxiv.org/abs/2508.03474). This is **2024–25, pre-fee data.**
- *Cheng, Yang & Zou, "Arbitrage Analysis in Polymarket NBA Markets" (arXiv 2605.00864, April 2026):*
  - **Data:** more than 75M order-book snapshots across 173 NBA games.
  - **Single-market:** only **7 executable single-market episodes**, with a median duration of **3.6 seconds**.
  - **Combinatorial:** 290 episodes, mostly in the final minutes of games, with a median return of 101 bp. 76.9% were limited to an average executable size of **14.8 shares**.
  - **Conclusion:** risk-free extraction is "limited to retail scale." The excerpt seen does not mention fees. — [arXiv 2605.00864](https://arxiv.org/abs/2605.00864)
- *Practitioner and vendor claims:* arbitrage windows reportedly shrank from about 12 s (2024) to about 2.7 s, and "73% of arbitrage profits are captured by bots executing in under 100 ms". These are vendor or blog claims repeated across sites with no published method, so treat them as unverified. — [TurbineFi blog](https://www.turbinefi.com/blog/prediction-market-arbitrage-latency-speed-2026); [Medium (Illumination)](https://medium.com/illumination/beyond-simple-arbitrage-4-polymarket-strategies-bots-actually-profit-from-in-2026-ddacc92c5b4f)

### Inferences
- The roughly $40M figure for 2024–25 almost certainly overstates what is capturable today, for four reasons:
  1. It assumed zero fees.
  2. It grouped fills up to an hour apart, which counts sequential non-atomic fills as arbitrage.
  3. Its single-condition YES+NO component cannot appear in today's mirrored book. It is likely an artefact of VWAP over time or of fills at different moments.
  4. Most of the money was in NegRisk events of the 2024 election cycle, when many-outcome books were thin and new.
- With fees at 3–5% of a basket, the gross mispricing must exceed rate × (1 − Σp²). A 3-outcome soccer market at 0.05 needs a sum of asks of about 0.97 or less; a 20-outcome futures market needs about 0.955 or less. Live books sit at 1.02 or more (asks) and 0.99 or less (bids). The arbitrage band is now wider than the typical spread, so a passive bot with a $10–50K book would see near-zero riskless flow in steady state.
- What can still be captured is:
  - fleeting, sub-second dislocations after news or in live sports (literature: a few to a few hundred episodes, about 15 shares deep);
  - "near-arb" maker strategies: resting bids on every outcome so that fills sum to below 1 − fees. This is not riskless: only some legs fill, leaving a directional position. Makers pay no fee and earn a rebate.
- Fee-free geopolitics markets are the one place the fee hurdle disappears. But geopolitics events are a small share, and the one fee-free live candidate had $0.03 of edge.
- Augmented negRisk events (2,457, including the big 2028 presidential futures) routinely show sums of asks of 0.85–0.95. They look like large arbitrages to naive scanners but are bets that an unlisted candidate will not win.

### Gaps
- There is no time-series of opportunities. Four snapshots over 12 minutes cannot measure frequency or lifetime of sub-second arbitrage; that would need a WebSocket recorder (`wss://ws-subscriptions-clob.polymarket.com`) over days. No independent 2026 measurement of negRisk arbitrage frequency after the fees was found.
- No source was found that quantifies how much arbitrage profit was extracted after the fee rollout (fees on crypto from January 2026, then other categories).
- It was not verified whether Polymarket's 2026 "Protocol V2" (Router / NegRiskModule, referenced in the docs) changed conversion mechanics or costs.

## Q2. Cross-venue arbitrage: Polymarket vs Kalshi, Polymarket US, and sportsbooks / betting exchanges

### Takeaway
Cross-venue gaps of 1–3¢ are common, larger gaps (2–4% median, up to 7¢ in the 2024 election) are documented in research, and they persist far longer than intra-venue arbitrage (minutes to hours). But combined taker fees take about 2.5–3¢ at mid prices. Resolution-wording mismatches are the main tail risk, and capital is split across venues and locked until resolution. In live checks, Kalshi and Polymarket Fed-decision prices were within 0–2¢, and every gap was negative after fees.

### Cited Findings

**Live data (2026-10-09, about 22:40 UTC)**

*Fed decision (5 outcomes)*

| Meeting | Polymarket | Kalshi | Gap |
|---|---|---|---|
| October | "No change" 0.83/0.84 | "Fed maintains rate" 0.83/0.84 | Identical |
| December | "No change" 0.22/0.23; "25bp hike" 0.74/0.75 | maintains 0.24/0.25; hike 0.73/0.74 | about 1¢ |
| January | "No change" 0.64/0.65 | maintains 0.62/0.63 | about 1¢ |

- **December trade:** buy Polymarket YES "No change" at 0.23 and Kalshi NO "maintains" at 0.76, for 0.99 gross. After fees (Polymarket 0.05 × 0.23 × 0.77 = 0.89¢; Kalshi 0.07 × 0.76 × 0.24 = 1.28¢) the net is about **−1.2¢**.
- **January trade:** the mirror trade nets about **−1.8¢**.
- Sources: [Kalshi markets API](https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker=KXFEDDECISION-26DEC), Polymarket CLOB; own computation.

*BTC "above K" at 7 PM ET, 9 Oct*
- Polymarket and Kalshi KXBTCD-26OCT0919 were compared at 22:37 UTC, 23 minutes before expiry. The two settle on different indices (Polymarket on Binance BTCUSDT 1-min close; Kalshi on CF Benchmarks BRTI).
- Prices agreed within spreads. Kalshi was tighter on in-the-money strikes (0.99/1.00 vs Polymarket 0.955/0.999). No locked arbitrage was found. — [Kalshi events API](https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXBTCD), own computation.
- Kalshi's daily BTC contracts settle at 5 PM EDT and Polymarket's daily "above" contracts at 12 PM ET. They are not the same contract and cannot form a riskless pair. — [Kalshi events API](https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXBTCD), Gamma `endDate` 16:00 UTC.

*Fees on each side*
- **Kalshi:** general fee round_up(0.07 × C × P × (1−P)), maximum about 1.75¢ per contract; makers pay about 25% of the taker fee. Third-party guides conflict on whether sports carry a lower rate. — [pm.wiki Kalshi fees](https://pm.wiki/uk/learn/kalshi-fees-explained); [rivermarkets](https://www.rivermarkets.com/insights/kalshi-fees.html). Not confirmed from Kalshi's own fee schedule.
- **Polymarket:** taker rates 0.07 crypto; 0.05 sports, economics, culture, weather and other; 0.04 finance, politics, mentions and tech; 0 geopolitics. Makers pay 0 and receive 15–25% rebates. — [Polymarket fee docs](https://docs.polymarket.com/polymarket-learn/trading/fees)

**Literature**
- *Gebele & Matthes, "Semantic Non-Fungibility and Violations of the Law of One Price in Prediction Markets" (arXiv 2601.01706, Jan 2026; data to Aug 2025, 10 venues):*
  - **Coverage:** about 6% of 102,275 events have a cross-platform counterpart; about 8% of Polymarket markets have an equivalent elsewhere, versus about 2% of Kalshi's.
  - **Size of gaps:** median execution-adjusted deviations of **2–4% from parity**, even in liquid constructions.
  - **Election case:** in the 2024 Polymarket–Kalshi election pair, spreads averaged **about $0.03, reaching $0.07** for sustained periods. Annualised returns ran from single digits to several hundred percent depending on lock-up.
  - **Cause:** the authors attribute the persistence to semantic non-fungibility, differing resolution rules (e.g. NYC weather: Central Park vs LaGuardia) and capital lock-up, not to disagreement about outcomes.
  - **APYs:** high APYs are "driven primarily by short market horizons … rather than substantial mispricing." — [arXiv 2601.01706](https://arxiv.org/html/2601.01706v1)
- *Vendor and blog claims, unverified and commercially motivated:*
  - Kalshi–Polymarket spreads of 2–5% on major events, compressing to 0.5–2% and closing within minutes in liquid markets; under 2¢ after fees is "marginal". — [predictionmarketspicks](https://predictionmarketspicks.com/articles/cross-platform-arbitrage-prediction-markets); [dropstab](https://news.dropstab.com/research/kalshi-vs-polymarket); [launchpoly](https://launchpoly.com/blog/polymarket-kalshi-arbitrage-guide)
  - 1–2¢ gaps routinely open during the NBA Finals. — [XCLSV](https://xclsvmedia.com/kalshi-vs-polymarket-arbitrage-2026-nba-finals-sharp-bettors/)
  - Polymarket and Kalshi resolved the 2024 government-shutdown market in opposite directions because of rule wording. — reported in [laikalabs](https://laikalabs.ai/prediction-markets/polymarket-kalshi-arbitrage-guide) / [getarbitragebets](https://getarbitragebets.com/blog/prediction-markets-arbitrage-guide). Not checked against primary sources.
  - Polymarket's Fed markets use change buckets while Kalshi's Fed product is "a rate-threshold ladder". Today's live data shows Kalshi also lists a 5-bucket KXFEDDECISION series that matches Polymarket one to one. — [laikalabs](https://laikalabs.ai/prediction-markets/polymarket-kalshi-arbitrage-guide); live Kalshi API.

**Polymarket US vs international Polymarket**
- Polymarket US is a separate, CFTC-regulated DCM/DCO with its own central limit order book and a fiat product. The international site is close-only for US users. Its fees follow a symmetric p(1−p) model with a taker maximum of about $1.50 per 100 contracts, and makers earn a rebate (third-party summary). — [Polymarket US docs](https://docs.polymarket.us/getting-started/what-is-polymarket-us); [docs.polymarket.us market data](https://docs.polymarket.us/concepts/market-data); [ats.io summary](https://ats.io/prediction-markets/polymarket/liquidity/)
- No price comparison between Polymarket US and international Polymarket was found. One operator generally cannot legally use both: the US venue is for US persons, and the international venue blocks them. This container's IP is geoblocked for international trading.

**Sportsbooks and betting exchanges (Pinnacle, Betfair)**
- No academic head-to-head study was found. Vendors (odds-API sellers) claim 3–8% divergences and slower reaction to news on Polymarket. — [sportsgameodds](https://sportsgameodds.com/use-cases/prediction-market-arbitrage-api); [oddspapi](https://oddspapi.io/blog/?p=2536). These are unverified and commercially motivated.

### Inferences
- **Break-even gap:** about 2.75¢ at mid prices for Polymarket politics (0.04) plus Kalshi (0.07); about 3¢ for sports at 0.05; less at extreme prices. A $10–50K bot can only profit on gaps of 3–4¢ or more, or by posting the maker leg on one venue to avoid its fee and earn a rebate. That brings back leg risk.
- **Matched contracts are where the gaps live but are hardest to automate:** subtly different rules, settlement times and indices (e.g. BRTI vs Binance; 5 PM vs noon). This is the same semantic risk that produced false positives in this scan.
- **Capital efficiency is poor:** both legs must be fully funded on separate venues (USDC on Polygon vs USD at Kalshi) until resolution. A 2¢ edge locked for 60 days is about 12% annualised before fees and failures. The trade suits short-dated markets: sports, daily economics, the Fed a few weeks out.
- **Sportsbooks:** sportsbooks limit winning accounts, and Betfair charges commission (typically 2–5% of net winnings; not verified here). Betting-exchange arbitrage against Polymarket is plausible in principle but unproven in public data.

### Gaps
- Kalshi was compared on only two families (Fed, BTC 7 PM). No broad matched-pair scan of sports or politics was done because matching contracts needs semantic matching.
- Kalshi's official fee schedule, including sports rates and maker fees, was not confirmed from a primary source.
- No public data was found on Polymarket US order books or prices, nor on Pinnacle or Betfair vs Polymarket spreads from a credible source.

## Q3. Polymarket crypto "above K" markets vs Deribit options-implied probabilities

### Takeaway
Polymarket's daily BTC and ETH "above K" ladders track Deribit-implied probabilities closely. Across 44 liquid strikes (Oct 10–15), the median absolute difference between Polymarket mid and Deribit was **1.3¢**, against a median Polymarket bid-ask spread of 3¢. In-the-money strikes are slightly cheap on Polymarket (about −1.5¢) and far-OTM tails slightly rich (+0.2–1.6¢). This is a model-dependent relative-value signal, not a riskless arbitrage. The total fee-adjusted edge versus the model at top of book was about **$60**, mostly from selling far-OTM lottery tails a few tenths of a cent rich.

### Cited Findings
- **Method:**
  - Deribit's public `get_book_summary_by_currency` (BTC 950 options; daily expiries 10, 11, 12, 13 and 16 Oct, 08:00 UTC) was used for mark IV of OTM options per strike.
  - Total variance was interpolated linearly in time to Polymarket's resolution time (16:00 UTC = 12 PM ET).
  - P(S > K) was computed as a smile-consistent digital: the numerical derivative of Black-76 call prices with the forward taken from Deribit's `underlying_price`.
  - Sources: [Deribit API](https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option); Polymarket CLOB books; own computation.
- **Examples at 22:41 UTC:**

  | Contract | Polymarket bid/ask | Deribit-implied |
  |---|---|---|
  | BTC > 82k, Oct 10 | 0.85 / 0.86 | 0.859 |
  | BTC > 84k, Oct 10 | 0.039 / 0.040 | 0.020 |
  | BTC > 82k, Oct 12 | 0.66 / 0.67 | 0.684 |
  | BTC > 84k, Oct 12 | 0.20 / 0.21 | 0.183 |
  | ETH > 2500, Oct 13 | 0.44 / 0.48 | 0.476 |

  Fee-adjusted edges versus the model (crypto rate 0.07) are almost all negative. The exceptions are buying BTC > 82k on Oct 11 (+1.1¢, 34 shares) and selling BTC > 84k on Oct 10 (+1.6¢, 501 shares on the bid). — own computation; data in `crypto_vs_deribit.csv`.
- **Oct 16:** the newly listed Oct 16 ladder had only 5-share quotes with 0.1/0.9-wide spreads and was excluded as illiquid. — own computation.
- **Resolution mismatch:**
  - Polymarket daily "above" markets resolve on Binance BTCUSDT 1-minute candles at 12:00 ET.
  - Deribit options settle on the Deribit index (30-minute TWAP before 08:00 UTC).
  - Kalshi uses CF Benchmarks BRTI.
  - So every hedge carries basis, timing and USDT/USD risk. — [Kalshi events API](https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXBTCD) (settlement source field); Polymarket market description (Gamma). Deribit settlement method is from general knowledge, not re-verified here.
- **Fee context:** dynamic taker fees on short-dated crypto markets were introduced in January 2026 explicitly to curb latency arbitrage against spot exchanges. — [TurbineFi (secondary)](https://www.turbinefi.com/blog/prediction-market-arbitrage-latency-speed-2026); live `feeSchedule` shows crypto at rate 0.07 (`crypto_fees_v2`).

### Inferences
- The 0.07 crypto rate makes a 1–2¢ model edge on a 50¢ contract (fee 1.75¢) uneconomic for takers. Only maker quoting informed by Deribit is plausible. That is market making with a fair-value model, not arbitrage, and it competes with the top ~50 crypto makers identified in the companion market-making study (`/home/user/test/pm_mm_check/REPORT.md`).
- **Hedging lumpiness:** Deribit's minimum option size is 0.1 BTC (about $8.3K notional at $82.6K). A $10–50K operator cannot cleanly delta- or vega-hedge small Polymarket positions, so in practice the trade is unhedged relative value.
- The systematic pattern (ITM about 1.5¢ cheap, OTM tails rich) is consistent with a favourite–longshot bias or with basis between Binance and Deribit's forward. It is too small to survive fees as a taker.

### Gaps
- One snapshot only. No historical study comparing Polymarket "above" prices with Deribit-implied probabilities was found.
- SOL and XRP were not compared (Deribit's USDC-settled alt options were not pulled).
- The Binance-vs-Deribit-index basis at Polymarket's resolution time was not measured.

## Q4. Execution realities for a $10–50K automated operator: fees, gas, settlement, capital lock-up, competition

### Takeaway
The binding constraints are now the taker fee (2.5–4.5¢ per riskless basket), sub-second competition and shallow depth (about 15 shares in the NBA study; $0–$22 per opportunity in this scan). Capital lock-up until resolution also matters. Pure riskless arbitrage is not a viable standalone business at $10–50K in October 2026. The remaining edges are probabilistic (maker near-arbs, cross-venue with matched rules, relative value against options) and need market-making-style infrastructure.

### Cited Findings
- **Fee formula:** fee = C × feeRate × p × (1−p); takers only, makers pay 0 with 15–25% rebates; geopolitics fee-free. — [Polymarket fee docs](https://docs.polymarket.com/polymarket-learn/trading/fees). Live Gamma `feeSchedule` agrees, with exponent 1 and `takerOnly` true (own data; see also `/home/user/test/pm_mm_check/REPORT.md`).
- **Order sizes:** the minimum order is 5 shares and ticks are $0.01 or $0.001 per market (Gamma `orderMinSize`, `orderPriceMinTickSize`). Many residual "arbs" are 5–60 shares deep (own data).
- **Non-atomic legs:** the Saguillo et al. paper stresses that "each of the above trades is non-atomic; thus, there is always some risk." — [arXiv 2508.03474](https://arxiv.org/html/2508.03474)
- **Concentration:** in 2024–25, the top account made $2.01M and the top 10 about $8.2M of the about $39.6M. — [arXiv 2508.03474](https://arxiv.org/html/2508.03474)
- **Depth limits:** the NBA study found a median duration of 3.6 s for single-market episodes and 14.8 shares of average executable size for 77% of combinatorial ones. — [arXiv 2605.00864](https://arxiv.org/abs/2605.00864)
- **NegRisk conversion:** "A No share in any market can be converted into 1 Yes share in every other market", and the conversion is atomic. This lets a buy-all-NO basket be unwound before resolution instead of locking capital. — [Polymarket neg-risk docs](https://docs.polymarket.com/developers/neg-risk/overview)
- **Capital lock-up and returns:**
  - In this scan, the residual buy-all candidates had 20–114 days to resolution (ECB 20 days, Hormuz 114 days). The 2028 presidential "arbs" had 760 days. — own data (Gamma `endDate`).
  - Gebele & Matthes note that headline APYs are driven by short horizons, not large mispricings. — [arXiv 2601.01706](https://arxiv.org/html/2601.01706v1)
- **Geoblocking:** this US-based container's IP is geoblocked for trading on international Polymarket (read-only APIs work), and Polymarket US is a separate venue. — task notes; [Polymarket US docs](https://docs.polymarket.us/getting-started/what-is-polymarket-us)
- **Gas and relayer costs:** not found in the fee docs, which only say there are no Polymarket deposit or withdrawal fees. — [Polymarket fee docs](https://docs.polymarket.com/polymarket-learn/trading/fees)

### Inferences
- **What a $10–50K operator can run, in order of realism:**
  1. **Near-arb maker baskets** in 3-outcome sports and 5-bucket macro events. Rest bids so the sum stays below about 0.98–0.99, with no maker fee plus rebates; flatten or hedge leftovers. This is market making with a basket constraint; expect returns of tenths of a percent per filled basket and leg risk.
  2. **Cross-venue Polymarket–Kalshi on carefully matched, short-dated contracts** (Fed, CPI, sports), taking only gaps of 3–4¢ or more, ideally with the maker leg on one side. Expect a few opportunities a week at $100s–$1,000s of size. This is inferred from the 1–2¢ live gaps and the 2–4% median deviations in the literature, not measured.
  3. **Event-driven sub-second captures** after news or in live sports. This needs co-located low-latency infrastructure; the literature suggests depth of about 15 shares.
- **Order-of-magnitude capturable profit:** this scan's riskless residual was about $1. The NBA study's 290 combinatorial episodes at about 101 bp on about 15 shares are worth a few dollars each. Even optimistically, pure riskless arbitrage on Polymarket looks like hundreds to low thousands of dollars per month for a well-built bot. This is an inference from the measured depth, not a measured P&L.

### Gaps
- No primary 2026 source covers gas or relayer costs, settlement times (UMA liveness, dispute rates) or Protocol V2 changes. Those were not verified in this session.
- No public on-chain measurement of 2026 arbitrage-bot P&L after the fees was found. Leaderboard-based claims (e.g. "14 of the top 20 wallets are bots", "$271K latency arb in 30 days") come from blogs without method and are unverified. — [laikalabs](https://laikalabs.ai/prediction-markets/polymarket-bots-vs-humans); [predik.io](https://predik.io/en/blog/bot-trading-polymarket-exploit-latencia-arbitraje-en)
