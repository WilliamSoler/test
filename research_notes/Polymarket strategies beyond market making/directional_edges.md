# Systematic directional / informational edges on Polymarket (as of Oct 2026)

Scope: repeatable "take a position" strategies (calibration/favourite-longshot, weather models, sports vs sharp books, mentions/tweet-count niches, end-of-market/resolution plays), backtested on resolved Polymarket markets (Jun 5 - Oct 3 2026) with public APIs, plus web/academic evidence. Written for a $10-50K automated operator.

**Own-data provenance (applies to every "own backtest" bullet below; source URLs are the public APIs):**
- Market universe: Gamma `/markets/keyset?closed=true` for 25 sample days (every 5th day, 2026-06-05 .. 2026-10-03) = 519,960 closed markets, 512,267 clean binary markets — [Gamma API](https://gamma-api.polymarket.com/markets/keyset).
- Price histories: CLOB `/prices-history` (10-min fidelity; 1-min for 5m/15m crypto) for 27,606 markets with volume >= 1,000 shares, stratified by group (caps: 4,000 moneyline, 3,000 weather, 1,500 each 5m/15m crypto, etc.) — [CLOB prices-history](https://clob.polymarket.com/prices-history). This is a *mid/display price*, not an executable quote, so "at mid" results overstate what a taker gets.
- Executed trades: Data API `/trades?takerOnly=true` for 2,494 markets (~130 random markets per group, 17 truncated at the 10k-offset cap), 1.05M taker fills — [Data API trades](https://data-api.polymarket.com/trades). Taker return = (payoff - price - fee)/price; maker return = the counterparty's P&L per $ at risk, with no rebate credited (conservative for makers).
- Fee model: per-market `feeSchedule` from Gamma (rate x p x (1-p), exponent = 1 in all Jun-Oct 2026 markets checked).
- CIs: 95% cluster bootstrap by event (ev_slug), 300-1,000 resamples. Scripts and tables: `/tmp/claude-0/-home-user-test/0ced0027-bcc3-524f-9ed3-ebcec6816192/scratchpad/dir/` (calib_summary.md, calib_tables.md, strategy_tables.md, trade_tables.md, wx_analyze.py, wx_blend.py). The per-group summary table is also copied to `directional_edges_calib_appendix.md` next to this file.
- Groups: categories come from Gamma `feeType`. "zero" = zero-fee markets, which in this sample are almost all college football (cfb-2026) spreads/totals. "nofee" = mostly geopolitics/world events plus some legacy markets. Sports horizons are measured to `gameStartTime`; all other horizons are measured to `endDate`.

---

## Q1. Calibration / favourite-longshot bias by category, and expected return per $ after fees (taker vs maker)

### Takeaway
Polymarket in mid-2026 is close to calibrated overall. Pooled non-sports recalibration slopes run 0.92-1.10 depending on horizon, and the favourite-longshot bias (FLB) is small. The executed-trade data does show a consistent tilt: **takers who buy longshots under 10c lose heavily, and the makers who sell them earn about +2.5 to +6% per $**. Near-certain favourites (0.90-0.98) are slightly underpriced only close to resolution and only in some categories (mentions, finance, culture/posts, economics, tech). At 24-72h out the same favourite bands lose money net of fees, and sports spreads/totals favourites lose at every horizon. Many headline "edges" are smaller than a 1c half-spread, so most of them are only capturable as maker orders.

### Cited Findings
**Fee regime (context for every after-fee number):**
- Taker fees began on crypto on Jan 5 2026 (15-min contracts first, all crypto timeframes by Mar 6), on sports on Feb 18 2026, and on almost every other category on Mar 30 2026. Geopolitics/world events stay fee-free. Makers pay nothing and get a rebate share (20% crypto, 25% most categories, 50% finance at rollout) — [Pine Analytics, "Polymarket Fee Rollout"](https://pineanalytics.substack.com/p/polymarket-fee-rollout).
- Pine reported category-specific exponents at the March rollout (2 for mentions/other, 0.5 for economics/weather). In the Gamma `feeSchedule` of Jul-Sep 2026 markets, **every category has exponent 1**. Rates: crypto 0.07 (rebate 0.20); weather, culture, economics and general 0.05 (rebate 0.25); politics, finance, tech and mentions 0.04 (rebate 0.25); zero_fees 0. Sports moved from `sports_fees_v2` (rate 0.03, rebate 0.25) to `sports_fees_v3` (rate 0.05, rebate 0.15) between about Jul 10 and Jul 25 2026, and v3 was ~99% of sports markets by August. An NFL/CFB-specific `sports_fees_nfl_cfb_oct26` type appears in the Oct 3 sample — own data, [Gamma API](https://gamma-api.polymarket.com/markets/keyset). This conflicts with Pine's March figures, so the API values (Jul-Oct) should be treated as current.
- A taker rebate programme (tiered by 30-day weighted volume, paid daily) went live May 28 2026 — [Polymarket docs: taker rebates](https://docs.polymarket.com/programs/taker-rebates.md).

**Own backtest: price-history calibration (mid price at horizon, one observation per market; logistic recalibration y ~ a + b*logit(p); b>1 means favourites are underpriced):**
- POOLED non-sports, non-up/down (10k markets, ~3.1k events): b = 1.10 [1.04,1.16] at 1h before end; 0.99 [0.94,1.05] at 6h; 0.95 [0.90,1.00] at 24h; 0.92 [0.86,0.99] at 72h; 1.05 [0.96,1.15] at 7d. So prices are slightly too extreme a day or more out and slightly too timid in the final hour — [own data, CLOB prices-history](https://clob.polymarket.com/prices-history).
- Categories with b significantly above 1 (favourites underpriced): finance at 1h 1.42 [1.28,1.65]; mentions 1.55 [1.18,2.58] at 1h, 1.23 [1.02,1.55] at 24h and 1.44 [1.15,1.89] at 72h; tech at 24h 1.39 [1.15,2.19]; weather at 1h 1.10 [1.01,1.22]; geopolitics/"nofee" at 1h 1.39 [1.15,2.06].
- Categories with b below 1 (prices too extreme): sports spreads 0.80 [0.64-0.97] at 1h, 6h and 24h pre-game; zero-fee CFB markets about 0.55 [0.28,0.87] (only 96 events, horizon relative to endDate so partly in-play). Not significantly different from 1: politics 0.92-0.99, sports moneyline 0.94-0.96, crypto strike 0.91-1.07, 5m/15m crypto up/down 0.92-1.05.
- Favourite band 0.90-0.98, return per $ bought at mid (maker, no fee), pooled non-sports: **+1.7% [+0.3,+2.7] at 1h** before end; -0.3% [-1.6,+0.9] at 6h; **-1.5% [-2.8,-0.1] at 24h**; -1.5% [-3.1,0.0] at 72h. Taker with a 0.5c half-spread plus fee: +1.0% [-0.1,+2.0] at 1h and -2.2% [-3.4,-1.1] at 24h.
- The same favourite band by category (maker at mid):
  - mentions: +3.8% [+0.3,+5.6] at 1h; +5.2% [+2.6,+6.8] at 24h (84 bets); +5.8% [+5.2,+6.5] at 72h (34 bets).
  - finance: +4.1% [+3.1,+4.9] at 1h, but -3.1% [-7.3,+0.4] at 24h.
  - economics: +3.4% [-0.4,+6.4] at 24h; +3.5% [+0.4,+5.9] at 72h.
  - tech: +4.9% [+4.3,+5.5] at 24h.
  - sports_spreads: -5.3% [-8.9,-1.2] at 24h.
  - sports_totals: -3.6% [-6.5,-0.4] at 1h.
  - sports_other: -2.7% [-5.1,-0.5] at 1h.
  - zero-fee CFB: about -12% (wide CI).
- Raw bucket calibration, pooled non-sports, 24h before end: the 0.65-0.80 bucket wins 67.7% vs a 72.4% price (excess -4.7pp [-8.5,-1.2]). The 0.20-0.35 bucket wins 32.3% vs 27.4% (+4.9pp [+1.2,+8.6]), so mid-range favourites are mildly *overpriced* at 24h, which is a reverse FLB. At 1h, 2-5c longshots win 0.94% vs a 3.09% price (-2.15pp [-2.80,-1.33]); at 24h the same bucket wins 5.6% vs 3.2% (+2.4pp [+0.7,+4.1]). Longshot pricing has no stable sign across horizons.

**Own backtest: executed taker trades (dollar-weighted; 2,494 markets):**
- All groups, non-sports, before scheduled end (882k fills, $66M taker cost, 1,402 events), taker return after fee by bucket:
  - <0.02: +110% [-99,+549] (noise from a few hits)
  - 0.02-0.05: **-74% [-94,-38]**
  - 0.05-0.10: -53% [-87,+26]
  - 0.90-0.95: +1.7% [-5.6,+5.6]
  - 0.95-0.98: +1.6% [-0.4,+2.8]
  - 0.98-0.995: -0.6% [-2.4,+0.7]
  - The makers on the other side of 2-5c longshot buys earned **+2.5% [+1.1,+3.2]**, and +3.8% [-2.8,+6.4] at 5-10c.
  - Overall, takers earned +2.2% [-0.9,+5.7] and makers -2.9% [-6.6,+0.4]. Takers are not systematically losers on Polymarket in this period, which differs from Kalshi (below).
- Category detail (taker = buyer of the given price bucket):
  - **mentions** before end: takers +4.4% [+1.9,+7.8] and makers -7.2% [-13.7,-3.3]. Takers buying 0.90-0.95 made +7.5% [+6.4,+8.4], 0.95-0.98 +2.1% [+0.6,+3.0], and 0.98-0.995 +1.2% [+1.1,+1.3]. Takers buying under 5c lost about 100%.
  - **culture_posts** (tweet/Truth Social counts): favourite takers made +4.7% [+2.9,+7.7] at 0.90-0.95, +3.0% [+2.3,+3.3] at 0.95-0.98, and +1.1% at 0.98-0.995. Makers selling 5-10c longshots earned +6.1% [+4.3,+8.0].
  - **weather**: takers +1.5% [-0.4,+3.7] and makers -3.4% [-6.0,-0.5]. Taker 0.90-0.95: +5.1% [+1.6,+7.4]. Makers selling longshots (0.05-0.10 bucket) earned +3.6% [-2.9,+7.8].
  - **crypto 5-minute up/down**: takers -2.7% [-4.1,-1.2] overall, but +3.3% [+2.5,+3.6] at 0.95-0.98 and +1.15% [+1.11,+1.19] at 0.98-0.995. Takers buying under 10c lost 90-107%, and makers selling them earned +0.9 to +6.4%. The 15-minute version: takers -3.3% [-6.2,-0.4] overall.
  - economics: makers -2.1% [-3.6,-0.3].
  - finance: about 0 (+-1%).
  - politics: takers +1.1% [-2.8,+1.8].

**Academic / benchmark context:**
- On Polymarket's full 2022-11 to 2026-04 on-chain tape (1.2B trades, $61B), mean (payout - price) per trade by price decile is:
  - 0.00-0.10: -0.0023
  - 0.10-0.20: -0.0019
  - 0.20-0.30: -0.0032
  - 0.70-0.80: +0.0076
  - 0.80-0.90: +0.0098
  - 0.90-1.00: +0.0056
  - This is a classic FLB, but tiny: under 1c per share, before fees. The same paper reports that the top 1% of maker addresses hold 84.1% of maker volume, and that maker concentration rose after maker rebates were introduced in Feb 2026 — [Qin & Yang, "Polymarket-v1 Database", arXiv 2606.04217](https://arxiv.org/abs/2606.04217).
- Using 353M trades on Kalshi and Polymarket, political markets are persistently *underconfident* (prices compressed toward 50%). On Polymarket, politics has a mean slope of 1.45, sports 1.06 and crypto 1.06. Weather markets (Kalshi) are *overconfident* at short horizons (slopes 0.69-0.97 within 48h). Roughly half the raw slope variation is estimation noise under event clustering — [Le, "Decomposing Crowd Wisdom", arXiv 2602.19520v2 (Aug 2026)](https://arxiv.org/abs/2602.19520).
- On Kalshi (2021-11/2025), takers average -1.12% and makers +1.12% excess return. 5c contracts win 4.18% (-16% mispricing) and 95c contracts win 95.83%. The taker-maker gap by category is finance 0.17pp, politics 1.02pp, sports 2.23pp, weather 2.57pp, crypto 2.69pp, entertainment 4.79pp and media 7.28pp — [Becker, "The microstructure of wealth transfer in prediction markets"](https://jbecker.dev/research/prediction-market-microstructure).
- An SSRN study of 124M Polymarket trades ($48B) finds prices "accurate most of the time", with biases such as overtrading the default/"Yes" option — [Investment Officer summary of Reichenbach & Walther (SSRN 5910522)](https://cms.investmentofficer.com/en/news/prediction-markets-prove-accurate-enough-help-investors-german-study-finds) (secondary coverage; original paper not read).

### Inferences
- **Longshot selling as a maker** is the most consistent tilt in 2026 executed trades: about +2.5 to +6% per $ at risk in crypto up/down, culture_posts, weather and pooled non-sports. The economics are poor, though. You put up 90-98c to earn 2-10c, a rare loss costs the full stake, and bootstrap CIs on zero-loss samples are too tight. For example, 0 losses in 57 trades still allows a true loss rate up to about 5% (rule of three), which is above the roughly 3.5% break-even for 96.5c favourites.
- **Favourite "bonding" works only close to resolution** (about 1h before end, or after the decisive information arrives) and in categories where the outcome becomes near-deterministic before the official end: mentions, culture_posts, finance closes, economics, tech. That is "information already out, price not yet at 1", i.e. a speed and attention game. It is not a structural bias you can harvest 24-72h out, where the same bands lose 1.5-2% at mid.
- Sports spreads/totals favourites are overpriced (slope about 0.8). The mirror trade is to sell favourites, i.e. buy underdogs at 20-35c on spreads. Mid-based returns for that are positive but the CIs span 0 (e.g. sports_spreads 24h longshot side +40% [-12,+90]). It needs validation against Pinnacle closing lines before acting.
- The taker fee of rate x p(1-p) is small at the extremes: 0.04 x 0.95 x 0.05 = 0.19c per share at 95c. The half-spread is the binding cost for favourite strategies, and a passive maker bid captures most of the measured +1 to +5%.

### Gaps
- `prices-history` gives the displayed/mid price, not the best ask, so taker-executable returns at a horizon were approximated with an assumed 0.5-1c half-spread. Order-book snapshots at the same horizons would be better and were not collected.
- Maker fills were assumed at mid with no adverse selection in the price-history tests. The trade-level maker returns do include adverse selection but exclude rebates (15-25% of taker fees).
- Sample: 25 days (1 in 5), Jun-Oct 2026. Some groups are small (mentions 56-66 events, culture_posts 64, economics ~120), so category results are suggestive, not robust.
- The Reichenbach & Walther SSRN paper was not read directly. No 2026 Polymarket-only calibration paper using post-fee data was found.

---

## Q2. High-probability bonding, end-of-market and post-scheduled-end strategies

### Takeaway
Buying 95-99.5c outcomes in the last hour earns about +0.1% to +3% per trade where the outcome is effectively known before the market closes (crypto 5m final minute, mentions, tweet counts, finance closes). Post-scheduled-end "stale" prices in finance markets look like large edges on mid-price data, but almost nothing trades there, so they are display artifacts. The real money is in fast execution on new information (e.g. the word was said, the count was crossed), which favours low-latency bots, and capital is tied up until UMA resolution.

### Cited Findings
- Price-history "favourite bonding" at 1h before end, buying the 0.95-0.98 band with a 0.2c half-spread plus fee (own backtest, [CLOB](https://clob.polymarket.com/prices-history)):
  - finance +3.08% [+2.93,+3.21] (241 bets, 159 events)
  - mentions +3.16% (49 bets)
  - economics +3.41% (29)
  - culture_posts +2.79% (24)
  - all with a 100% win rate in-sample
  - pooled non-sports +1.40% [+0.40,+2.14] (857 bets, 98.4% wins)
  - Pooled at 24h: -2.16% [-3.59,-0.79]
  - Pooled, the 0.95-0.98 bucket at 1h wins 99.0% (626 obs, 442 events) vs a break-even of about 96.9%. That margin survives a Poisson bound on 6 losses (upper bound about 1.9% loss rate).
- Crypto 5-minute up/down, 1 minute before end, 0.95-0.98 band: +3.35% [+3.13,+3.55], 57/57 wins at mid. Executed taker fills at 0.95-0.98 in 5m markets: +3.25% [+2.53,+3.64]; at 0.98-0.995: +1.15% [+1.11,+1.19] (own trade data, [Data API](https://data-api.polymarket.com/trades)). This is consistent with the prior finding that 5/15-min takers are informed over 1-5 minute horizons.
- Post-scheduled-end (market still open), finance at 5 min after endDate, at mid: the 0.50-0.65 bucket wins 78.9% (+46% net), and 0.90-0.95 wins 100% (+9.0%). However, executed taker volume after the scheduled end in sampled finance markets was only **$8.5K across 52 events**, with taker return +0.07% [-0.96,+0.60]. The mid-price "edge" is stale quotes, not tradable liquidity (own data).
- Executed trades after the scheduled end, all non-sports: takers -3.9% [-6.8,+2.8], makers +3.5% [-2.9,+6.0] ($5.9M, 774 events). Mentions after end: takers +4.1% [+0.6,+6.9] (24 events). Weather after end (pre-resolution): +0.3% [-0.4,+1.1].

### Inferences
- The "high-probability bonding" yield is real but thin. About +1 to +3% gross per trade, held for minutes to hours plus the resolution lag (UMA liveness about 2h; disputes take days), gives an attractive annualised rate only with high turnover. Capacity per market is small.
- The edge comes from reacting to resolution-relevant information faster than resting liquidity reprices: transcripts and live streams for mentions, XTracker counts for tweets, exchange closes for finance. A $10-50K bot can compete in long-tail markets where the big makers are absent. Tail risk comes from rule nuance (what counts as a "mention", replies vs posts) and rare -100% outcomes.

### Gaps
- Time from scheduled end to `closedTime` and to payout was not measured, so the annualised return of bonding was not computed.
- Fill probability for passive bids at 95-99c near the end was not modelled.

---

## Q3. Weather (daily high-temperature bucket markets) vs public forecast models

### Takeaway
In 11 US cities (Jun 15 - Oct 5 2026), the market beat a calibrated forecast model built on the NWS National Blend of Models (NBS) station forecast by a wide margin. The model added **no information** beyond the market price. Model-vs-market trading rules lost money after spread and fees. Weather prices look well calibrated and already absorb standard model guidance. Practitioner profit claims are mostly unaudited and come from longshot lottery wins.

### Cited Findings
- Own backtest (wx_analyze.py, wx_blend.py):
  - 1,231 city-day events, ~12k bucket markets ([Gamma events](https://gamma-api.polymarket.com/events) with slug `highest-temperature-in-<city>-on-<date>`), with prices from [CLOB prices-history](https://clob.polymarket.com/prices-history).
  - Forecast: NBS 12Z MOS daily max (`txn`) from the [Iowa Environmental Mesonet MOS API](https://mesonet.agron.iastate.edu/api/1/mos.json) for the resolution stations (KLGA, KORD, KMIA, KATL, KDAL, KSEA, KLAX, KBKF, KHOU, KAUS, KSFO).
  - Method: a Gaussian bucket model with per-city bias and sigma fitted on data before Aug 10 and tested after (616-627 test events). Snapshots were at 15:00 UTC the day before ("day-ahead") and on the day ("same-day").
- Brier score (lower is better): day-ahead market 0.671 vs model 0.762; same-day market 0.610 vs model 0.733. Log-loss: market 1.36 vs model 1.67 day-ahead; 1.18 vs 1.56 same-day.
- Logistic regression y ~ logit(market) + logit(model), event-clustered: day-ahead market coefficient 1.07 [0.95,1.18] and model coefficient **-0.03 [-0.14,+0.09]**; same-day market 1.07 [0.96,1.19] and model **0.00 [-0.09,+0.10]**. The forecast carries zero incremental information.
- Trading rule (buy when model minus ask > threshold): at 0.5c half-spread, returns range from -7.9% to +2.6% per $ with every CI spanning 0. At 1-2c half-spread, -5.6% to -21.9%, with several CIs entirely negative (e.g. same-day, 2c, threshold 3%: -21.9% [-31.4,-11.6]).
- Market calibration at the day-ahead snapshot:
  - 0-5c: price 0.9% vs win 0.8%
  - 5-15c: price 8.7% vs win 8.4%
  - 15-35c: price 24.8% vs win 23.5%
  - 35-65c: price 45.7% vs win 45.4%
  - That is well calibrated, consistent with the price-history slope of 0.98 [0.88,1.10] at 24h. At 1h before end the slope is 1.10 [1.01,1.22], mildly underconfident.
- Executed weather trades: takers +1.5% [-0.4,+3.7] and makers -3.4% [-6.0,-0.5] before end. That points to some informed taking (likely live station observations on the day), not stale forecast mispricing.
- Practitioner evidence (unaudited):
  - An open-source bot ([tobiasbischoff/polymarket-weather-bot](https://github.com/tobiasbischoff/polymarket-weather-bot)) compares NOAA/Open-Meteo to prices and reports an 8-day backtest (Feb 3-10 2026) with a 58.7% win rate and 15.2% ROI.
  - A GFS-ensemble bot lists highest profits of about $1.8k ([suislanchez/polymarket-kalshi-weather-bot](https://github.com/suislanchez/polymarket-kalshi-weather-bot)).
  - A vendor (WeatherBot) claims $3.37M of member P&L, self-reported ([weatherbot.bot](https://weatherbot.bot/)).
  - A viral "$88K weather strategy" analysis reports the bot had 1,537 losses vs 349 wins, with profit driven by a few 5c longshot hits, e.g. about $30K on a Paris market (per search snippet of [Medium/mountain-movers](https://medium.com/mountain-movers/inside-the-data-behind-polymarkets-viral-88k-weather-prediction-trading-strategy-and-results-2e65a8389f37); the page returned 403 to direct fetch).
- On Kalshi, weather markets are *overconfident* at short horizons (slopes 0.69-0.97 within 48h) — [Le 2026](https://arxiv.org/abs/2602.19520). That is not replicated on Polymarket US cities here (0.98-1.10).

### Inferences
- An edge from public deterministic forecasts (NBS/GFS/ECMWF via Open-Meteo) is not supported in 2026 US-city markets. Prices already embed this guidance, and the 5% fee rate plus 1-2c spreads remove any residual.
- Remaining plausible weather edges:
  - Same-day nowcasting from live METAR/ASOS observations. Observations of the running max make high buckets impossible or certain intraday. This is consistent with weather takers being slightly informed.
  - Station and rounding nuances (Weather Underground resolution source, °C international cities).
  - Maker liquidity on the long tail of international °C cities.
  - None were tested here.

### Gaps
- Open-Meteo (forecast, historical-forecast and previous-runs APIs) returned "Daily API request limit exceeded" from this container's shared IP, so Open-Meteo ensembles (ECMWF/GFS/ICON) were not tested. NBS is itself a multi-model calibrated blend, so it is a reasonable proxy.
- International °C cities (London, Paris, Seoul, Ankara, Wellington, Lucknow, Munich, etc. are in `weather_stations.json`) were not backtested.
- Intraday METAR nowcasting was not backtested.

---

## Q4. Sports: Polymarket vs sharp sportsbooks (Pinnacle) and in-play latency

### Takeaway
No published head-to-head study of Polymarket vs Pinnacle closing lines was found. Own data shows pre-game moneylines are near-calibrated (slope about 0.95) and spreads are overconfident (slope about 0.80). In-play, takers beat makers on moneylines by about 10% per $, which is an informed-flow/latency signature despite the sports order delay. For a small operator the realistic sports edge is *sharp-line-anchored* pricing (de-vigged Pinnacle as fair value). Pure calibration bets on sports favourites lose after the 5% v3 fee rate.

### Cited Findings
- Pre-game calibration slopes (own data, [CLOB](https://clob.polymarket.com/prices-history)):
  - moneyline: 0.94 [0.87,1.03] at 1h, 0.96 at 6h, 0.96 at 24h (2.1-3.5k events)
  - totals: 0.91-0.93 (n.s.)
  - spreads: **0.80 [0.64,0.95] at 1h**, 0.80 [0.68,0.96] at 6h, 0.80 [0.64,0.97] at 24h
  - Favourite 0.90-0.98 bands lose: spreads -6.0% [-10.0,-2.7] as taker at 24h; totals -4.3% [-7.8,-1.5] at 1h; sports_other -3.5% [-5.6,-1.2] at 1h.
- Executed trades, in-play/post-start: on moneylines, **takers +10.8% [+1.0,+17.1] and makers -9.4% [-14.4,-0.8]** (49k fills, 128 events). sports_other in-play: takers -5.3% [-11.5,+0.4]. Spreads and totals in-play: n.s. (own data, [Data API](https://data-api.polymarket.com/trades)).
- Polymarket sports markets apply a delay to marketable orders. One page says 3 seconds, with a 1-second taker delay being tested on NBA/MLB; another describes a 250 ms window. The per-market `secondsDelay` field is authoritative. Resting limit orders are auto-cancelled at game start — [Polymarket docs: Limit Orders](https://docs.polymarket.com/polymarket-learn/trading/limit-orders), [Order Lifecycle](https://docs.polymarket.com/concepts/order-lifecycle).
- A Crypto.com prediction market added a 3-second delay to protect makers from courtsiding. TV/stream feeds lag live action by 5-8s typically, and up to 48s for Super Bowl LX streaming — [SBC News](https://sbcnews.co.uk/latestnews/2026/05/20/cost-stream-delay-live-betting/), [Streaming Media](https://www.streamingmediaglobal.com/Articles/Post/Blog/Why-the-Gap-Between-the-Game-and-Your-Screen-Is-a-Business-Problem-173851.aspx).
- No published Polymarket-vs-Pinnacle closing-line study exists. Vendors describe using de-vigged Pinnacle as fair value for trading Kalshi/Polymarket. Pinnacle restricted its public API in July 2025, so sharp odds come via aggregators — [OddsPapi backtest tutorial](https://oddspapi.io/blog/?p=2489), [odds-api.io](https://odds-api.io/blog/pinnacle-api-shutdown-alternatives).
- Sports volume grew after fees were introduced: daily volume went from $100-150M to $150-250M — [Pine Analytics](https://pineanalytics.substack.com/p/polymarket-fee-rollout). In the own sample, sports are about 85% of resolved market count, with ~12k "sports_other" markets per day.

### Inferences
- The in-play maker loss (about -9%) means quoting in-play without a fast data feed is the losing side. A taker with a sub-delay data advantage (official data feeds, courtside) is the winner. That is not repeatable for a typical $10-50K bot unless it buys low-latency sports data.
- The spreads overconfidence (slope 0.8) suggests a "fade the spread favourite / buy cheap side" rule. Its mid-based return is positive but not significant, so it needs Pinnacle-line confirmation.
- With v3 fees (rate 0.05, peak 1.25c at 50c), a pre-game edge has to exceed about 1.25c plus the half-spread at mid-range prices. That is plausible only when Polymarket lags sharp-line moves (news, injuries), which argues for maker quotes anchored to Pinnacle, not taker sniping.

### Gaps
- No Pinnacle odds history was available in this environment, so Polymarket vs Pinnacle was not tested directly.
- In-play latency was not measured directly. The `secondsDelay` values per market were not sampled.

---

## Q5. Mentions / speech-word markets, Elon/Trump post-count markets, other niche modelable markets

### Takeaway
These are the categories where the 2026 data most clearly shows *favourites underpriced and takers making money*. Mentions takers earned +4.4% [+1.9,+7.8] after fees, and favourites at 90-98c paid +2 to +7.5%. Post-count markets show the same pattern at 90-99c. Capacity is tiny: mentions trade about 80k shares per day across all markets, and edges depend on transcript/base-rate research and on fast reaction to live speech or counts.

### Cited Findings
- Mentions price-history (own data):
  - recalibration slope 1.23-1.55 (>1, significant at 1h, 6h, 24h and 72h)
  - favourites 0.90-0.98 bought at mid: +3.8% at 1h, +5.2% [+2.6,+6.8] at 24h, +5.8% [+5.2,+6.5] at 72h (34-93 bets, 30-66 events)
  - longshots under 10c as taker: -87% to -104%. Low-probability words almost never hit.
  - Sources: [CLOB](https://clob.polymarket.com/prices-history), [Data API](https://data-api.polymarket.com/trades).
- Mentions executed trades (51 events, $175K taker cost): takers +4.4% [+1.9,+7.8] and makers -7.2% [-13.7,-3.3]. Taker 20-35c: +62% [+6,+134]; 0.90-0.95: +7.5% [+6.4,+8.4].
- Culture_posts (tweet/Truth Social count buckets): slope about 1.0-1.2 (n.s.). Executed: favourite takers +4.7% [+2.9,+7.7] at 0.90-0.95 and +3.0% [+2.3,+3.3] at 0.95-0.98; makers selling 5-10c longshots +6.1% [+4.3,+8.0].
- Market sizes (own Gamma sample, per day; volume in shares):

  | Market type | Markets/day | Volume (shares)/day | Median volume per market |
  |---|---|---|---|
  | Mentions | ~67 | ~0.08M | ~630 |
  | Culture_posts | ~34 | ~1.6M | — |
  | Economics | ~17 | ~0.4M | — |
  | Tech | ~28 | ~2.3M | — |
  | Weather | ~827 | ~3.6M | — |
  | 5m crypto | ~2,162 | ~20.5M | — |
- Elon tweet markets: weekly bucketed events resolved by XTracker. Only main-feed posts, quotes and reposts count (not replies), and deleted posts count if captured (about 5 min). Volume is reportedly $20-50M per week. A community strategy buys the bucket containing XTracker's pace projection plus its neighbours. No backtested returns were published — [pm.wiki Polymarket Elon tracker](https://pm.wiki/uk/projects/polymarket-elon-tracker), [skills.sh polymarket-elon-tweets](https://www.skills.sh/openclaw/skills/polymarket-elon-tweets).
- On Kalshi, "media" and "entertainment" categories have the largest taker-maker gaps (7.28pp and 4.79pp, makers winning) — [Becker](https://jbecker.dev/research/prediction-market-microstructure). Polymarket 2026 mentions show the *opposite* sign: takers win.

### Inferences
- The mentions/posts pattern fits informed takers who watch live events and transcripts (or count trackers) and lift stale maker quotes at 90-98c after the outcome is effectively decided. The repeatable strategy is to monitor live sources and buy the decided side the moment it is decided, plus base-rate modelling of word frequency (prior transcripts, speaker habits) for pre-event pricing.
- Small markets make this a good fit for a $10-50K operator, but per-market capacity is a few hundred to a few thousand dollars.
- Stale maker quotes are the counterparty. Providing liquidity in mentions without live monitoring loses about 7%.

### Gaps
- No pre-event base-rate model for mentions (e.g. from transcripts) was backtested. Only the market's own calibration was measured.
- No independent audited P&L for tweet-count strategies was found. The XTracker pace model was not backtested.

---

## Q6. Resolution / UMA disputes and edge cases

### Takeaway
Disputes are rare: about 0.05-0.06% of resolved markets in the sample, roughly 280 of 520k. They are concentrated in high-stakes geopolitical and count markets, where UMA voters resolve on the literal market text and confirmation within the window. That creates occasional large "rules-lawyering" edges, but also tail risk for bonding strategies, and outcomes depend on a concentrated set of voters.

### Cited Findings
- In the own Gamma sample (519,960 closed markets), `umaResolutionStatuses` include a "disputed" step for roughly 280 markets (about 0.05%). Examples:
  - "US x Iran permanent peace deal by June 15, 2026?" ($177M volume, disputed twice, resolved YES)
  - "Iran closes its airspace by June 15?" (disputed three times)
  - a Truth Social post-count bucket
  - several tennis/esports props
  - 209 markets were still "proposed" at collection time
  - Source: [Gamma API](https://gamma-api.polymarket.com/markets/keyset).
- The Strategy (MSTR) "sells bitcoin by May 31, 2026" market was disputed twice. UMA voters resolved May as NO and June as YES based on the disclosure date, although a filing showed 32 BTC sold May 26-31. Polymarket said confirmation outside the timeframe does not qualify — [The Defiant](https://thedefiant.io/news/markets/usd85m-polymarket-dispute-over-strategy-s-may-bitcoin-sale-puts-uma-s-token-voting-oracle-on), [Cointelegraph](https://regional-front.cointelegraph.com/news/polymarket-dispute-strategys-bitcoin-sale-resolves-no).
- Reported concentration: about nine whale addresses hold about half of UMA voting power and side with the winning outcome in nearly all disputes. Over 1,150 Polymarket markets triggered arbitration in 2026 by about June, exceeding all of 2025. A WSJ analysis reportedly found at least 60% of active UMA voters linked to Polymarket accounts — [KuCoin/BlockBeats](https://www.kucoin.com/news/flash/polymarket-dispute-resolutions-dominated-by-9-whale-addresses-critics-raise-concerns?lang=en_US), [Finance Magnates](https://www.financemagnates.com/fintech/polymarkets-arbitration-model-faces-conflict-of-interest-questions/) (secondary reporting; WSJ original not checked).

### Inferences
- A "resolution-literalism" strategy can be positive EV in a handful of high-volume markets per month: read the rules, and buy the side UMA is likely to choose when the crowd prices the "spirit" outcome. It is not systematic and not backtestable at scale.
- For favourite-bonding bots, disputes and rule ambiguity are the main source of -100% tail losses. Excluding markets with ambiguous rule text (e.g. "permanent deal", "closes airspace") is prudent.

### Gaps
- Price paths around disputes, and whether the crowd or the UMA outcome was "right" ex post, were not analysed systematically.
- The 1,150 arbitration figure (from secondary sources) conflicts in scale with the about 280 disputed markets in the 1-in-5-day sample (about 1,400 implied over Jun-Oct). Definitions likely differ.

---

## Q7. Academic and practitioner evidence on Polymarket efficiency (2024-2026), and bottom line for a $10-50K operator

### Takeaway
The academic consensus is that Polymarket is broadly calibrated, with a small FLB under 1c per share before fees, domain-specific slopes (politics underconfident), and a concentrated maker class. Directional strategies such as mean-reversion and wallet-copying fail after costs. For a small automated operator, the evidence-backed positive-EV directional plays in Oct 2026 are narrow:
- near-resolution favourite bonding and information-reaction in mentions, post-count, finance and 5m crypto markets (about +1 to +5% per trade, small capacity)
- maker-side longshot selling (about +2.5 to +6% per $ at risk, tail-heavy)

Weather-forecast, broad calibration and sports-favourite strategies are not supported after fees.

### Cited Findings
- On 2024 US election markets, a Bocconi Students Investment Club study found order flow has persistent positive price impact (Kyle's lambda > 0). Mean-reversion after large trades produces "near-zero profits", wallet copying "performs even worse", and directional strategies "fail after transaction costs". Passive market making was profitable (simulated Sharpe 7-12) — [BSIC, "Polymarket Microstructure Analysis" (2026)](https://bsic.it/wp-content/uploads/2026/10/Polymarket-Microstructure-Analysis.pdf).
- On the Polymarket-v1 database, high-spread niche markets attract informed specialists, and the Gibbs spread negatively predicts Brier score — [Qin & Yang 2026](https://arxiv.org/abs/2606.04217).
- On calibration, politics on Polymarket is underconfident (slope about 1.45), while sports and crypto are near 1.06 — [Le 2026](https://arxiv.org/abs/2602.19520). Own 2026 data does not confirm politics underconfidence at 1h-7d horizons (0.92-0.99, n.s.; about 230 events).
- Own data summary of candidate strategies (per $ staked, 95% CI):
  - "Nothing ever happens" (buy NO priced under 65c in non-sports Yes/No markets, 1c half-spread): -3.6% [-15,+8] at 24h; -22% [-35,-7] at 1h — [own data](https://clob.polymarket.com/prices-history).
  - Favourite bonding 0.95-0.98 at 1h, pooled non-sports: +1.4% [+0.4,+2.1].
  - Weather model trading: negative.
  - Mentions favourites 0.90-0.98: +3.8 to +5.8%.
  - Maker longshot selling 2-5c, pooled: +2.5% [+1.1,+3.2].
  - In-play sports making: -9.4%.

### Inferences
- **Most promising for $10-50K, in order:**
  1. Event-driven "decided-outcome sniping" in mentions, post-count, finance and economics markets: live transcript, XTracker and exchange-data monitors, buying 90-99c sides as soon as the outcome is decided. Positive in both price-history and executed trades; small per-market capacity, but many markets per day.
  2. Passive maker bids on near-certain sides (equivalently, selling longshots) in the last hours, in categories with slope above 1: mentions, finance, tech, economics, geopolitics. This avoids taker fees and earns rebates, but needs strict per-market exposure caps because of -100% tails and disputes.
  3. Final-minute 5m/15m crypto favourites at 95-99c. Executed takers earn +1.2 to +3.3%, but a direct latency race against Binance-feed bots.
- **Not recommended on this evidence:**
  - generic FLB or "nothing ever happens" contrarian bets
  - weather forecast-model trading against prices
  - pre-game sports favourites
  - in-play sports quoting
  - post-end "stale mid" plays (illiquid)
- Overall, expected net returns are low single-digit percent per trade. Annualised returns depend on turnover and on how fast UMA payouts recycle capital.

### Gaps
- Strategy-level annualised returns and capacity (fill rates, queue position) were not simulated, and no order-book replay was done.
- The fc26 paper "Are Decentralized Prediction Markets Efficient? Evidence from Bitcoin Options" (Financial Cryptography 2026 DeFi workshop) could not be text-extracted beyond its title — [FC26 PDF](https://fc26.ifca.ai/defi/papers/market-efficiency-prediction-markets.pdf).
- Polymarket's own sports-market `secondsDelay` values and the exact maker rebate amounts paid were not checked from live data.
