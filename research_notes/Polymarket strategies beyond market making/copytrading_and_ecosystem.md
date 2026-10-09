# Copy-trading / smart-money following on Polymarket, and non-trading business routes (as of Oct 9, 2026)

Scope note: quantitative results below are this researcher's own analysis of Polymarket's public APIs (data-api, user-pnl-api, gamma, CLOB prices-history), run Oct 9, 2026 from a read-only, US-geoblocked container (no orders placed). Scripts and raw outputs are in the session scratchpad `ct/` folder (build_universe.py, fetch_pnl.py, persistence.py, copysim.py, post2.py, persistence_results.json, copysim_50_*.json, raw_notes_backup.md). The file `kfee.pdf` from the earlier attempt is NOT a Kalshi fee schedule. It is a saved "Vercel Security Checkpoint" HTML page, so I discarded it.

## Q1. Do leaderboard winners stay profitable out of sample, and can a copier make money after fees and latency?

### Takeaway
Wallet PnL persists only weakly: Spearman rank correlation between consecutive periods is 0.09–0.26. Top wallets typically earn 5–30% of their formation-period dollars in the next period, and about 40% of top-10 wallets simply stop trading. Copying the top-50 wallets' taker buys was profitable in only 1 of 4 monthly out-of-sample tests (Aug→Sep, about +11% at a 1-minute delay). Averaged across tests it was about −3% at 1 minute and −4% to −6% at 5–15 minutes, size-weighted and net of taker fees. Any edge decays within about 5 minutes and is negative at 60 minutes in every test. Copy-trading is therefore not a reliable standalone strategy for a $10–50K operator. At best it is a noisy, regime-dependent signal in sports markets that needs sub-minute execution and strict wallet filtering.

### Cited Findings
**How I built the wallet universe and measured PnL**
- Universe: all wallets seen in `/trades` for the 400 highest-volume markets that ended Apr 1–Jul 31 2026 (`gamma /markets?closed=true`) with at least $500 sampled notional. That gives 16,702 wallets. I took the 5,000 largest by sampled notional. Selection uses no data after Jul 31.
- PnL: daily cumulative PnL from `user-pnl-api.polymarket.com/user-pnl?interval=all&fidelity=1d`. 4,417 wallets returned a series; 583 (12%) returned an empty series and were excluded.
  - The empty-series wallets were mostly single-market wallets (median 1 market, versus 4 for the others), so one-shot wallets are under-represented. That is a survivorship-type bias.
  - PnL is in dollars and includes mark-to-market; it is not a percentage return.
- Source: own analysis of [Polymarket Data API](https://data-api.polymarket.com) and user-pnl-api, Oct 9 2026.

**Persistence table (own analysis)**

| Formation → test | n active | Rank corr | Top-10 test: mean / median / %pos / %flat | Top-50 test: mean / median / %pos | Top-100 test: mean / %pos | Bottom-100 test: mean / %pos | All active %pos |
|---|---|---|---|---|---|---|---|
| Apr–May → Jun–Jul | 3,721 | 0.163 | $1.47M / −$18k / 40% / 10% | $404k / $35k / 56% | $214k / 50% | −$217k / 33% | 50% |
| Jun–Jul → Aug 1–Oct 8 | 4,061 | 0.103 | $307k / $0 / 40% / 40% | $126k / $0 / 38% | $60k / 46% | −$33k / 33% | 38% |
| Jul → Aug | 3,658 | 0.086 | $47k / $0 / 40% / 40% | $23k / $0 / 44% | $0.4k / 45% | −$25k / 31% | 40% |
| Aug → Sep | 2,916 | 0.262 | $252k / $71k / 80% / 0% | $204k / $72k / 74% | $101k / 69% | −$71k / 27% | 48% |
| Sep → Oct 1–8 | 2,777 | 0.173 | −$159k / −$2k / 40% / 0% | $15k / $0.3k / 50% | $12k / 53% | −$12k / 32% | 46% |

- Formation-period mean PnL for the top-10 was $0.66M–$3.8M. Only 26–38 of the formation top-100 were also in the test-period top-100.
- The top formation decile had a positive test mean in 4 of 5 splits. The bottom decile was negative in all 5. Losers keep losing more reliably than winners keep winning. — own analysis

**Profile of today's leaderboard** (own analysis, live `data-api.polymarket.com/v1/leaderboard?timePeriod=MONTH|WEEK&orderBy=PNL&limit=50`; "age" = days since the first point in the wallet's PnL series)
- Monthly top-50:
  - Median age 156 days; 32% are younger than 60 days.
  - 2 wallets are 7 days old or less. For example, "joseph00677" made $1.58M PnL in a 3-day-old account, and "mooseborzoii" made $1.44M in 8 days.
  - Median PnL/volume is 11.1%.
  - 36% had negative cumulative PnL before the 30-day window started.
  - Total PnL is $39.0M; the #50 wallet made $298k.
- Weekly top-50:
  - 30% are younger than 60 days; median PnL/volume is 11.3%.
  - 34% had negative cumulative PnL before the week.
  - The #50 wallet made $150k.
- In short, many leaderboard entries are high-variance or brand-new wallets rather than proven traders.

**Copy-trade simulation: method** (own analysis, copysim.py + post2.py)
- Leaders: the top-50 wallets by formation-period PnL.
- Signals: each leader's TAKER BUY fills in the test window (`/trades?user=&takerOnly=true`), aggregated per token per 60 seconds, with at most 120 sampled per leader.
- Copier price at delay D = leader's VWAP + (1-minute CLOB prices-history price at t+D − price just before the leader's fill). So the copier pays the same spread and impact as the leader plus the subsequent drift.
- The copier holds to resolution and pays the taker fee from each market's `feeSchedule`.
- Cleaning:
  - Excluded leader prices below 2c or above 98c.
  - Excluded signals where the price history hit the clamp or fell below half the leader's price within 15 minutes. These were mostly data glitches, such as "Will Iceland win" printing at 0.001 for 15 minutes, plus 5-minute crypto markets. This removed 428–612 signals per run.
- 95% confidence intervals come from a bootstrap that resamples leaders.
- Markets not resolved by Oct 9 are dropped, which biases the sample toward fast-resolving markets.

**Copy-sim results: net return per $ held to resolution, size-weighted (copier sizes proportionally to the leader)**

| Sim (leaders' formation period → copy window) | Clean signals / leaders | 0 min (leader's own price) | 1 min | 5 min | 15 min | 60 min |
|---|---|---|---|---|---|---|
| A: Jun–Jul → Aug 1–Oct 8 | 2,160 / 35 | −0.5% [−9.8, +13.0] | −2.1% [−10.6, +9.1] | −3.4% [−13.4, +5.4] | −5.0% [−13.8, +2.6] | −10.6% [−24.9, −5.8] |
| B: Aug → Sep | 2,456 / 38 | +12.5% [+0.7, +21.9] | +11.3% [−1.7, +20.9] | +10.1% [−3.4, +21.1] | +8.1% [−5.1, +18.2] | +1.9% [−12.2, +13.0] |
| C: Sep → Oct 1–8 | 1,674 / 39 | −9.6% [−27.3, +5.0] | −9.6% | −9.5% | −12.0% [−28.3, −1.0] | −11.9% |
| D: Jul → Aug | 1,599 / 31 | −8.2% | −10.5% | −12.5% | −15.0% | −31.2% [−39.9, −16.5] |
| Average of A–D | — | −1.5% | −2.7% | −3.9% | −6.0% | −13% |

**Copy-sim results: equal dollars per signal**
- A: 0 min +7.6%, 1 min +3.4%, 5 min −0.9%, 15 min −7.5%, 60 min −16.2%.
- B: +8.8%, +5.8%, +2.7%, −3.4%, −12.8%.
- C: −2.8%, −2.8%, −9.1% [−16.2, −2.7], −12.6% [−18.3, −6.7].
- D: +9.2% [+0.9, +19.4], +6.3%, +2.4%, −3.6%, −19.0%.
- Average: about +5.7% at 0 min, +3.2% at 1 min, −1.2% at 5 min, −6.8% at 15 min.
- So the leaders' small trades carry a small edge that is gone within about 5 minutes. — own analysis

**Supporting statistics from the copy-sims**
- Copier slippage versus the leader's VWAP, consistent across all four sims:

  | Delay | Median | Mean |
  |---|---|---|
  | 1 min | +0.5–0.85c | +1.2–1.5c |
  | 5 min | +1c | +2.2–2.7c |
  | 15 min | +1c | +3.6–4.1c |

- Average taker fee was 1.9% of notional at the leader's price: sports 2.4%, crypto 4.1%. — own analysis
- Leaders positive (size-weighted, among those with at least 10 signals):

  | Sim | Leaders | Positive at 0 min | at 1 min | at 5 min |
  |---|---|---|---|---|
  | A | 32 | 16 | 16 | 15 |
  | B | 37 | 28 | 25 | 23 |

  — own analysis
- Results by category:
  - Sports was the largest bucket. In A it went −0.8% (0 min) → −2.4% (1 min) → −4.0% (5 min) size-weighted, with equal-$ at +12.4% [+0.2, +24.2] at 0 min. In B it went +9.8% → +7.9% → +7.0%.
  - Crypto fast markets could not be copied: A went −8% at 0 min, −52% at 5 min and −105% at 15 min.
  - No-fee and geopolitics markets lost money in A (−5% to −6% size-weighted) but were positive in B (+10%). — own analysis
- Taker share of leaders' notional in the test window was 60% (median) in A and 54% in B. Only 4–13 of 50 leaders were more than 80% taker. The rest of their flow is maker fills, which a copier cannot replicate at the same price with taker orders. — own analysis

**Fees used** (live gamma `feeSchedule`; [Polymarket fee docs](https://docs.polymarket.com/trading/fees.md))
- Fee = C × rate × p × (1−p), charged to takers only.
- Rates: crypto 0.07; sports 0.05 (`sports_fees_v3`) or 0.03 (`sports_fees_v2`, `sports_fees_nfl_cfb_oct26`); politics, finance, tech and mentions 0.04; economics, culture, weather and other 0.05; geopolitics 0.
- For a taker buy, the fee as a share of notional is rate × (1−p). At 50c that is 3.5% for crypto, 2.5% or 1.5% for sports, and 2% for politics.
- The [Taker Rebate Program](https://docs.polymarket.com/programs/taker-rebates.md) (live May 28 2026) refunds 3–50% of fees by 30-day weighted volume:
  - Bronze $2k → 3%; Silver $20k → 8%; Gold $200k → 18%; Platinum $1M → 32%; Diamond $4M → 44%; Obsidian $10M+ → 50%.
  - Category weights: sports 1.0, politics 1.3, economics 1.7, crypto 2.3.
  - A $10–50K copier would realistically reach Silver or Gold (8–18% back).

**Academic evidence**
- [The Block, Apr 26 2026](https://www.theblock.co/post/398902/skilled-polymarket-traders-are-a-3-minority-and-everyone-else-funds-their-gains-study), on a working paper by Gómez-Cram, Guo, Kung (London Business School) and Jensen (Yale):
  - Data: all Polymarket trades 2023–2025, covering 1.72M accounts and $13.76B.
  - 3.14% of accounts are "skilled winners". 44% of those stay skilled out of sample, versus about 10% for active mutual funds.
  - Only 12% of top earners are in the skilled group, and about 60% of "lucky winners" revert to losses out of sample.
- [Akey, Grégoire, Harvie, Martineau, CEPR DP21615, Jun 2026](https://econpapers.repec.org/RePEc:cpr:ceprdp:21615):
  - Data: 588M trades, $67B.
  - The top 1% of positive-PnL users capture 76.5% of profits.
  - Winners provide liquidity with limit orders; losers take liquidity with market orders.
  - Monthly performance is "modestly persistent, however this may represent sample selection rather than skill."
  - Insider trading is unlikely to explain the largest winners.

### Inferences
- Copying is structurally hard on Polymarket. The academic evidence says profitable accounts make money mainly as makers, and a copier can only follow them as a taker, paying the spread plus a 1.5–3.5% fee at mid-range prices. In my sims, the leaders' own taker buys netted only about −1.5% on average at their own fill prices.
- A dollar PnL leaderboard is a poor filter. It mixes whales sizing up, one-shot event bets and brand-new wallets (possible insiders), and roughly 40% of top-10 wallets go flat the following month. A better filter would mirror the academic "skill" approach:
  - wallets whose taker flow predicts short-term price moves;
  - consistent PnL as a percentage of volume;
  - at least 3 months of history;
  - high taker share.
  This is my suggestion and was not tested here.
- If attempted at all:
  - Restrict to sports and other non-crypto markets.
  - Copy within about 30–60 seconds. The detection path would be websocket or on-chain `OrderFilled` events; Polygon blocks are about 2 seconds, but I did not measure the end-to-end lag.
  - Size per signal rather than per leader's dollars, since equal-$ beat size-weighted in 3 of 4 sims.
  - Kill a leader after N losing signals.
  - Expect roughly zero to low single-digit returns per signal after fees, with large regime variance (sim B +11% versus sims C/D −10%).
- The noise floor is large. One month of about 2,000 signals from about 35 leaders gives roughly ±10–15 percentage-point confidence intervals, so a copier cannot quickly tell whether a leader set has edge.

### Gaps
- The 1-minute price-history granularity cannot resolve sub-minute copy latency. "Delay 0" is the leader's own price, an upper bound. I did not measure true order-book depth or impact for copier size; a $500–5k copier in thin sports books could slip more.
- Holding to resolution differs from mirroring the leader's exits. Exit-mirroring was not simulated.
- Signals in markets unresolved by Oct 9 are dropped, which biases toward short-dated markets, especially in sims A and C.
- 12% of wallets had empty PnL series. The cause is unknown, possibly an API limitation for some account types.
- Formation and test windows overlap across sims (A spans B and C's windows with a different leader set), so the four sims are not fully independent.
- I found no independent, audited performance data for any commercial copy-trading bot.

## Q2. Copy-trading tools and bots, reported results, and how insider-trading controversies affect a copy strategy

### Takeaway
There is a large ecosystem of copy-trading bots: Telegram bots, open-source GitHub repos, and whale-alert services. Usage is measurable through the builder leaderboard; for example, PolyCop has $368M all-time routed volume across 13,016 users. No tool publishes audited copier returns, and practitioner write-ups consistently cite slippage and latency as the failure mode. Insider-style wallets (fresh wallets making large, accurate bets on military and geopolitical events) are real and are a big part of the "smart money" narrative. However, they are one-shot, often in fee-free geopolitics markets, legally toxic to copy on Polymarket US, and their edge is gone once the information is public.

### Cited Findings
**Bot usage (live builder leaderboard, `data-api.polymarket.com/v1/builders/leaderboard`, Oct 9 2026; own pull)**
- PolyCop (Telegram copy-trading bot):
  - Weekly: $2.24M volume, 503 users.
  - October month-to-date: $3.32M, 620 users.
  - All-time: $368M, 13,016 users.
- Other trading front-ends, all-time: Kreo $90M / 9,060 users; Polygun $119M / 10,013; Polycule $47M / 3,110; Bullpen $65M / 2,999.
- Third-party listings (pm.wiki, an unverified aggregator): [Onsight](https://pm.wiki/projects/onsight) $377K / 133 users; PolyTap $3.1M / 38 users ([pm.wiki compare](https://pm.wiki/compare/onsight-vs-polytap-bot)).

**Open-source bots** (GitHub search "polymarket copy trading" returned 370 repos on Oct 9 2026)
- HarrierOnChain/Prediction-Markets-Trading-Bot-Toolkits: Rust, 473 stars, "Copy Trading is production-ready".
- braedonsaunders/homerun: Python, 201 stars, backtest and paper trading.
- Drakkar-Software/OctoBot-Prediction-Market: 117 stars.
- Abomination81/copybot: Rust, 111 stars, created Sep 12 2026.
- Many repos are keyword-stuffed SEO spam. — [GitHub](https://github.com/HarrierOnChain/Prediction-Markets-Trading-Bot-Toolkits); [GitHub](https://github.com/braedonsaunders/homerun)
- The [PolyCopy repo](https://github.com/laurensa453/PolyCopy) self-reports 42ms detection and 3.2% missed trades (unverified).

**Security warning**
- Malicious "Polymarket bot" campaigns in 2026:
  - A hijacked dev-protocol GitHub org hosted a bot that exfiltrated .env files and wallet keys — [StepSecurity](https://www.stepsecurity.io/blog/malicious-polymarket-bot-hides-in-hijacked-dev-protocol-github-org-and-steals-wallet-keys).
  - Nine npm packages from the account "polymarketdev" asked users for their private key — [SafeDep](https://safedep.io/malicious-polymarket-npm-crypto-wallet-drainer/); [OSV MAL-2026-4209](https://osv.dev/vulnerability/MAL-2026-4209).
  - A fake "polymarket-arbitrage-bot" spread through 30 npm packages, attributed to the North Korean "Contagious Trader" campaign — [ThreatCluster](https://threatcluster.io/cluster/malware-spread-via-fake-polymarket-trading-bot-targets-defi--efb72af6).

**Reported results**
- A MEXC news item describes a trader who made about $650k in 7 months by manually copying specialists. The same trader's first attempts lost money, and copying high-probability or "insider" traders led to consistent losses — [MEXC](https://www.mexc.com/news/666845).
- An example of copier entry slippage: a whale averages $0.44 while the follower buys at $0.48–0.50 — [startpolymarket](https://startpolymarket.com/strategies/copy-trading/). Some whales lose money, and large trades may be hedges — [QuickNode](https://www.quicknode.com/builders-guide/best/top-10-polymarket-whale-trackers).

**Insider controversies**
- Feb 2026: ZachXBT said 8 of the top 10 wallets in the Axiom market were likely insiders — [Cointelegraph](https://cointelegraph.com/news/suspected-insider-1-2m-zachxbt-axiom-expose).
- Mar 2026: six wallets created in February made about $1M on US–Iran strike markets, some buying hours before the strikes (flagged by Bubblemaps) — [Cointelegraph](https://regional-front.cointelegraph.com/news/polymarket-traders-1m-us-iran-strike-insider-trading-concerns).
- Apr 2026: Army Master Sgt. Gannon Ken Van Dyke was charged with using classified information to make about $410k. This is described as the first prediction-market insider-trading case — [ValueTheMarkets](https://www.valuethemarkets.com/cryptocurrency/news/insider-trading-investigation-shakes-polymarket-amid-millions-in-profits).
- May 2026: House Oversight Chair Comer demanded records from Polymarket and Kalshi — [report](https://san-1510.aid.brainsum.com/news/top-news/us-congress-starts-insider-trading-probe-prediction-markets).
- Aug 2026: the Anti-Corruption Data Collective flagged 556 "Orca" wallets. Of these, 152 made about $8M at a 97.2% win rate, mostly on US military and defense markets — [SMU/Inkl PDF](https://skbi.smu.edu.sg/sites/skbi.smu.edu.sg/files/%5Bcurrent-domain%3Amachine_name%5D/news_room/20260821_Inkl_Polymarket%20faces%20fresh%20insider%20trading%20scrutiny%20after%20152%20wallets%20allegedly%20made%20%248%20million%20betting%20on%20US%20military%20markets_%20report.pdf).
- Polymarket US explicitly bars trading on confidential information obtained through a breach of duty, and on material non-public information (MNPI) in some contracts — [PM US Trading Restrictions](https://docs.polymarket.us/learn/trading/access-and-limits/trading-restrictions.md).
- Polysights markets an "Insider Finder" tool — [polysights.xyz](https://polysights.xyz).

### Inferences
- Copying "insider" wallets is mostly unworkable:
  - The wallets are fresh, so they are not on any leaderboard before the trade.
  - They trade once and then vanish.
  - Signals cluster in fee-free geopolitics and military markets, where my sim A showed copied leaders losing (−5% to −6%).
  - Knowingly trading on others' misappropriated MNPI is legally risky, especially for a regulated-venue user.
- The realistic "smart-money" product is anomaly alerts (fresh wallet + large size + low price), sold as information. That is what Polysights, Polymonit and others already do.
- Copy bots make their money from builder fees on routed volume, not from users' returns.

### Gaps
- No copy-bot fee schedules were confirmed. PolyCop's base fee is not public in what I found; Polymart advertises a "10% discount on fees" without a base rate.
- I found no audited copier PnL from any vendor.

## Q3. Non-trading income: builder program, referrals, API terms, third-party tool revenue, selling data and signals

### Takeaway
The most concrete route is the Builder Program:
- You can charge up to 1% taker / 0.5% maker on routed flow, on top of Polymarket's fees.
- Verified builders can also win weekly USDC rewards and grants (amounts unpublished).
- Distribution is very top-heavy. The 25th builder does about $2M in 9 days (roughly $7M/month), so at a 0.5% fee a mid-ranked builder grosses roughly $30–35k/month at most, and the 50th roughly $5–6k/month.

Referral income is small: 10% of net fees, only for the referee's first 30 days. Selling raw data is a weak business because the APIs are free and Polymarket bought the leading data-API startup (Dome). Analytics and alert products monetize mainly by routing trades through builder codes.

### Cited Findings
**Builder fees** ([docs](https://docs.polymarket.com/builders/fees.md))
- Taker maximum 100 bps; maker maximum 50 bps; 1 bp granularity; default 0.
- Charged on top of platform fees and paid to the builder-profile wallet.
- The rate can change once every 7 days, and a change takes effect 3 days after scheduling.
- Polymarket can revoke fee rights or disable a builder code at its discretion. Fee rates are public.

**Builder tiers** ([docs](https://docs.polymarket.com/builders/tiers.md))

| Tier | Relayer transactions/day | Access | Extras |
|---|---|---|---|
| Unverified | 100 | No approval needed | — |
| Verified | 10,000 | Approval via builder@polymarket.com, "a few business days" | "Weekly USDC rewards based on volume" and "Grants (subject to approval)", leaderboard listing, private Telegram |
| Partner | Unlimited | — | Highest API rate limits |

- Gas is subsidized through the relayer. No dollar amounts are published for rewards or grants. The Builder overview says grants are competed for on the Builder Leaderboard — [overview](https://docs.polymarket.com/builders/overview.md).

**Builder leaderboard** (own pull, Oct 9 2026; "MONTH" is stamped dt=2026-10-01 and appears to be month-to-date)

| Window | Total, top-50 | Rank 10 | Rank 25 | Rank 50 |
|---|---|---|---|---|
| Week | $128.7M | $3.0M | $1.23M | $0.23M |
| Oct 1–9 | $200.4M | $4.8M | $2.06M | $0.34M |
| All-time | $7.35B | — | — | $12.5M |

- Week leaders: #1 betmoar $24.8M (337 users); traderline $14.4M (452 users).
- All-time leaders: betmoar $2.30B; Gate $864M; traderline $594M; PolyCop $368M; MetaMask $326M (39,078 users).
- Ranks 51–100 range from about $23k to $336k month-to-date.
- Several top "builders" have only 1–5 users (Gate 4–5, MagicMarkets 1, Jupiter 1). — own analysis of `data-api.polymarket.com/v1/builders/leaderboard`

**Referral programs**
- Polymarket international ([terms effective May 28 2026](https://docs.polymarket.com/programs/referral-program.md)):
  - The referrer needs at least $10k lifetime volume.
  - Pays 10% (direct) or 5% (indirect) of NET fees, after the referee's own tier rebate.
  - Only for the referee's first 30 days and only until the referee reaches Platinum.
  - 30-day click attribution; paid daily in pUSD; nothing on fee-free markets.
  - Integrations that use omnibus wallets are excluded; terms can change without notice.
- Polymarket US:
  - Refer-a-Friend pays a $25 credit to each side once the referee deposits at least $10, capped at 50 referrals (so at most $1,250 in credits) — [PM US FAQ](https://docs.polymarket.us/faqs/refer-a-friend-faqs.md).
  - A separate "Referral Incentive Program" for affiliates is by application, with contractual terms — [PM US incentives](https://docs.polymarket.us/incentives/overview.md).

**Data, analytics and signal businesses**
- Polymarket acquired Dome, a YC-backed unified Polymarket+Kalshi data API, confirmed Feb 19 2026; terms undisclosed — [The Block](https://theblock.co/post/390546/polymarket-buys-fresh-prediction-market-api-startup-dome-marking-second-official-acquisition). Reported prior funding conflicts: $500k YC + $4.7M seed (The Block) versus about $5.2M ([CasinoBeats](https://casinobeats.com/2026/02/20/polymarket-acquires-dome-to-expand-developer-tools-for-prediction-markets/)).
- Polysights:
  - Raised about $1.5M pre-seed in Jun 2026 (YZi Labs, Maven 11, Varys and others). One headline said $15M, which conflicts — [AICoin](https://www.aicoin.com/en/article/541587); [DiarioBitcoin](https://www.diariobitcoin.com/startups-verticales/polysights-respaldada-por-polymarket-recauda-usd-15-millones-para-frenar-irregularidades-en-mercados-de-prediccion/).
  - Its site advertises a Market Terminal, Insider Finder and Trading Terminal, and claims "$5.5B volume tracked". I found no public pricing page — [polysights.xyz](https://polysights.xyz).
- polymarketanalytics.com: returned 403 to my requests; no pricing or revenue found.
- Polymonit: a read-only whale-alert Telegram/email service with tiered pricing; amounts not stated — [QuickNode listing](https://www.quicknode.com/builders-guide/tools/polymonit-by-qoreon-labs-ltd).

**Terms of use**
- The polymarket.com trade attestation says users confirm they are not "(i) a U.S. person; (ii) located in the United States, France or other restricted jurisdiction; and (iii) using a VPN … Polymarket reserves the right to put your wallet in close-only mode". — polymarket.com page strings, fetched Oct 9 2026 ([polymarket.com/tos](https://polymarket.com/tos))
- The full ToS text on commercial API and data redistribution could not be retrieved (the page is JS-rendered).

**Maker-side programs** (context; covered elsewhere)
- [Maker rebates](https://docs.polymarket.com/programs/maker-rebates.md): 20% of taker fees in crypto, 15% in sports, 25% elsewhere; paid daily.
- [Liquidity rewards](https://docs.polymarket.com/programs/liquidity-rewards.md) include an August 2026 pool of $1M for crypto TWAP 5-minute/15-minute/4-hour markets (now ended).

### Inferences
- Builder fee arithmetic (assumes the whole volume is fee-eligible taker flow; the leaderboard's volume definition is unconfirmed):
  - Rank-25 builder: about $7M/month × 0.5% ≈ $34k/month; × 1% ≈ $69k/month.
  - Rank-50 builder: about $1.1M/month × 0.5% ≈ $5.7k/month.
  - PolyCop's October pace (about $11M/month) × 1% would be about $110k/month at most.
- In practice many builders charge less than the maximum. The builder fee also stacks on 1.5–3.5% platform taker fees, which pushes price-sensitive users away.
- Weekly builder rewards seem to be farmed by prop or MM shops tagging their own flow; those are the 1-user builders. A $10–50K operator running their own bot flow under a Verified builder code could plausibly collect some weekly USDC rewards on top of trading. The size of those rewards is unknown.
- Referral economics, worked example: a referee trades $100k of taker sports flow at about 50c in their first 30 days. That pays about $2.5k in fees, so the referrer earns roughly $230. Referrals only matter at audience scale (an influencer or a Telegram channel).
- Signals and data: the APIs are free and public, and Polymarket now owns Dome. Paid differentiation therefore has to come from analytics (wallet clustering, insider or anomaly detection, sports models) or from execution convenience routed through a builder code, not from raw data. Subscription pricing benchmarks were not found.

### Gaps
- Weekly builder USDC reward and grant amounts are unpublished.
- Actual builder fee rates per builder were not retrievable: the docs say they are public, but I could not find the endpoint.
- I found no revenue figures for PolymarketAnalytics, Polysights or the Telegram bots.
- Polymarket's API commercial-use and redistribution clauses could not be read.

## Q4. Access and legal: Polymarket international vs Polymarket US, geoblocks, KYC, US API and market-maker programs, and EU/Spain status

### Takeaway
- Polymarket international is closed or close-only in about 33 countries, including most large EU states.
- Polymarket US is a CFTC-regulated, KYC'd (SSN) venue for US persons only. It has:
  - a full Retail API and an institutional REST/gRPC API;
  - a by-application Market Maker Program;
  - open liquidity and volume incentive programs;
  - a new fee schedule from Oct 7 2026: 0.0695 taker, 0.0125 maker rebate.
- Spain is not on Polymarket's own geoblock list. However, Spain's gambling regulator (DGOJ) opened sanction proceedings against Polymarket and Kalshi on May 26 2026 and ordered ISPs to block both nationwide. I found no final resolution as of Oct 9 2026.
- For a Spain-based operator, trading Polymarket or Kalshi means operating against a Spanish regulatory block. Using a VPN to get around blocks breaches Polymarket's terms, which reserve close-only mode, and Polymarket reportedly blocks VPN IPs.

### Cited Findings
**Region table**

| Region | Polymarket international | Polymarket US | Kalshi | Notes |
|---|---|---|---|---|
| United States | Close-only (frontend + API) | Open to US persons; KYC with SSN; CFTC-regulated | Open (US) | polymarket.com: "Trading is blocked in the United States… Switch to polymarket.us" |
| Spain | Not on PM geoblock list, but DGOJ ordered a nationwide ISP block (BOE, May 26 2026); proceedings expected to take 3–4 months; no final decision found | Not available (US-only) | Also blocked by the same DGOJ order | DGOJ treats prediction markets as gambling that needs a Spanish licence |
| France | Close-only | No | Restricted / banned | Named in the PM trade attestation |
| Germany, Italy, Belgium, Poland, Slovakia | Close-only | No | Kalshi restricts Belgium and Poland (others vary) | |
| Ireland, Netherlands, Malta (sports only) | Close-only on frontend only; API not restricted | No | — | |
| UK, Australia, Singapore, Taiwan, Thailand, NZ, Brazil, Russia, Venezuela and others | Close-only | No | UK, Singapore, Taiwan, Thailand, Venezuela and Russia restricted | |
| Ontario, BC, Alberta, Quebec (Canada) | Close-only | No | Canada restricted | |
| Iran, Syria, Cuba, North Korea; Crimea, Donetsk, Luhansk | Fully blocked | No | — | |
| Other EU, e.g. Portugal, Sweden, Czechia | Open on the PM list (verify local law) | No | Kalshi says it is available in 140+ countries | |

**Sources for the region table**
- [Polymarket geoblock docs, fetched Oct 9 2026](https://docs.polymarket.com/api-reference/geoblock).
- Spain:
  - [Ministry press note](https://www.dsca.gob.es/en/comunicacion/notas-prensa/consumo-abre-expediente-sancionador-plataformas-polymarket-kalshi-ordena)
  - [CoinMarketCap](https://coinmarketcap.com/academy/article/spain-blocks-polymarket-kalshi)
  - [Euronews ES](https://es.euronews.com/2026/05/26/consumo-bloquea-cautelarmente-a-polymarket-en-espana-por-incumplimento-de-la-normativa)
  - [Cointelegraph](https://cointelegraph.com/news/spain-blocks-polymarket-kalshi-gambling-laws)
  - [Decrypt ES](https://decrypt.co/es/369147/espana-bloquea-polymarket-kalshi-licencia-juego-mercados-prediccion?amp=1)
  - [Geeknetic](https://www.geeknetic.es/Noticia/38738/Consumo-abre-expediente-a-Polymarket-y-Kalshi-ordena-bloquear-sus-webs-en-Espana-y-reabre-el-debate-europeo-sobre-los-mercados-de-prediccion.html)
- Kalshi international:
  - [Cointelegraph on the $300M raise and 140 countries](https://www.tradingview.com/news/cointelegraph:447497c7d094b:0-kalshi-raises-300m-to-expand-prediction-markets-to-140-countries/)
  - [Kalshi international eligibility](https://help.kalshi.com/en/articles/14026044-international-access-eligibility)
  - [SBC News](https://sbcnews.co.uk/featurednews/2025/10/14/kalshi-polymarket-growth/)

**Spain details**
- The DGOJ, part of the Ministerio de Derechos Sociales, Consumo y Agenda 2030, served notice via the official gazette (BOE) because it could not reach the companies at their foreign addresses.
- ISPs had 7–10 days to comply.
- The block covers users located in Spain.
- Polymarket said it is "committed to engaging constructively"; Kalshi declined to comment.
- One report said the sites were still reachable at the time and that the ministry had sought a judicial order. — [Cointelegraph](https://cointelegraph.com/news/spain-blocks-polymarket-kalshi-gambling-laws); [Geeknetic](https://www.geeknetic.es/Noticia/38738/Consumo-abre-expediente-a-Polymarket-y-Kalshi-ordena-bloquear-sus-webs-en-Espana-y-reabre-el-debate-europeo-sobre-los-mercados-de-prediccion.html)

**VPN enforcement**
- Polymarket reportedly blocks VPN-associated IPs (June 2026, citing The Information) — [Covers](https://www.covers.com/industry/polymarket-reportedly-tightens-vpn-rules-amid-rising-regulatory-pressure-june-1-2026); [Biometric Update](https://biometricupdate.com/202606/polymarkets-vpn-crackdown-puts-prediction-market-id-controls-under-scrutiny).

**Polymarket US KYC** ([signup docs](https://docs.polymarket.us/learn/get-started/signup.md))
- Sign up with Google or Apple, then provide date of birth, phone, legal name, address and SSN. An ID and selfie may be requested.
- KYC must be completed before depositing or trading. The venue is a CFTC-regulated exchange.

**Polymarket US API**
- Retail API with Python and TypeScript SDKs; keys are created in the app — [FAQ](https://docs.polymarket.us/learn/faq/api.md); [auth](https://docs.polymarket.us/api-reference/authentication.md).
- Rate limit is 25 requests/second per IP; RFQ quote creation and deletion are 100/second — [rate limits](https://docs.polymarket.us/api-reference/rate-limits.md).
- Institutional REST API at `api.prod.polymarketexchange.com`, with gRPC streaming, firm participant IDs and 3-minute access tokens — [institutional](https://docs.polymarket.us/institutional/introduction.md).
- Combos/parlays run on an RFQ system where market makers quote.

**Polymarket US fees** (effective Oct 7 2026, [fee schedule](https://docs.polymarket.us/fees.md))
- Taker fee = 0.0695 × C × p × (1−p) in all markets, except table tennis at 0.10.
- Maker rebate = 0.0125 × C × p × (1−p), paid at the time of the trade; there is no maker rebate on combos.
- Taker rebates based on prior-month taker volume: $250k–1M → 10%; $1–10M → 25%; $10M+ → 50%.
- "Accelerated Tier Placement" lets you prove volume on another prediction market to start at a higher tier.
- This supersedes the August category schedule reported by [River Markets](https://www.rivermarkets.com/insights/polymarket-us-fees.html) (0%, 4%, 5% or 7% taker by category; makers 0%).

**Polymarket US incentive programs** ([overview](https://docs.polymarket.us/incentives/overview.md); [liquidity](https://docs.polymarket.us/incentives/liquidity.md); [volume](https://docs.polymarket.us/incentives/volume.md))
- Liquidity Incentive Program (open):
  - Each second, a random snapshot scores resting orders as DiscountFactor^ticks × size.
  - Parameters include Target Size and an optional Max Spread.
  - Pools are set per period: pre-game, day-of, live and daily. The live schedule is at polymarket.us/rewards.
- Volume Incentive Program (open): based on taker notional at prices from 3c to 97c. Example: $100k per NBA Playoffs moneyline market for in-game trading, with a $500 minimum.
- Market Maker Program: by application.
- Referral/affiliate program: by application.

### Inferences
- For a Spain-resident operator:
  - Polymarket US is out, since it requires US-person KYC.
  - Polymarket international and Kalshi are under an active Spanish block.
  - The safest non-trading routes are those that do not require placing trades from Spain: building tools or data products, or acting as a builder/integrator. Even these may raise Spanish gambling-promotion and advertising questions. That needs Spanish legal advice; I did not research it.
- The Spanish proceedings' 3–4 month window ran out around September 2026. The status should be checked in the BOE or with the DGOJ before acting.

### Gaps
- I found no final DGOJ resolution, fine or court ruling (searched in English and Spanish).
- Whether Spanish residents face any personal liability was not addressed by any source; reports describe enforcement aimed at the platforms.
- Polymarket US Market Maker Program terms (rebates, obligations) are not public.
- Kalshi's exact list of 38 restricted jurisdictions is in its Member Agreement, which I did not retrieve.

## Q5. Kalshi as an alternative venue: fees, maker programs, API, and the incentive programs' end

### Takeaway
- Kalshi taker fees are 0.07 × C × P × (1−P), and maker fees are about 25% of that (0.0175) where charged. Kalshi has full REST/WebSocket APIs and a contractual Market Maker Agreement program.
- Kalshi filed with the CFTC on Sep 28 2026 to end its Volume Incentive Program no earlier than Oct 13 2026, amid wash-trading allegations about its perps volume. The Liquidity Incentive Program reportedly continues to Jan 1 2027 but excludes non-US users.
- Kalshi is also blocked in Spain.

### Cited Findings
**CFTC filing ending the Volume Incentive Program** — [CFTC filing](https://www.cftc.gov/filings/orgrules/rules09282630083.pdf) (primary)
- Kalshi's "Notice of Termination of the Volume Incentive Program", dated Sep 28 2026 and filed under Rule 3.13(f), says: "termination of this Program will go into effect no earlier than October 13, 2026".
- The program terms:
  - A fixed per-market Volume Reward per Eligible Term (at most 31 days), split pro rata by eligible volume.
  - Eligible volume is order-book trades at prices from $0.03 to $0.97; it may be restricted to the taker or maker side.
  - Rewards are capped at $0.005 per contract per participant.
  - Excluded: Kalshi affiliates, members that have signed a Market Maker Agreement, and introducing brokers / futures commission merchants (IBs/FCMs) and their customers.

**Program history and reported reasons**
- The program launched in March 2023.
- The Block linked the end to scrutiny of volume. It cited a WSJ report that the CFTC was examining repeated trades of about $5,500 that accounted for more than $5B of ETH-perps volume in a month. Kalshi says it is not under investigation and denies wash trading — [The Block, Sep 30 2026](https://theblock.co/news/business/2026-09-30-kalshi-ends-trader-incentive-program-417247); [SBC Americas](https://sbcamericas.com/2026/10/02/kalshi-end-volume-rewards-scrutiny/).
- Sources conflict on the previous end date: Oct 1 2027 per [Unchained](https://unchainedcrypto.com/kalshi-ends-its-trader-volume-rewards-a-year-early-amid-wash-trading-allegations/), versus Sep 1 2027 in an August 2026 filing ([CFTC](https://www.cftc.gov/filings/orgrules/rules08042613748.pdf)).

**Liquidity Incentive Program** ([Kalshi help](https://help.kalshi.com/en/articles/13823851-liquidity-incentive-program))
- Rewards of $1–$1,000 per day per market.
- Scoring uses a once-per-second snapshot, with orders weighted by distance from a Reference Price determined by Target Size (100–20,000 contracts) and a Discount Factor.
- The program ends Jan 1 2027 and can be changed at any time.
- Excluded: non-US users, IBs/FCMs, and Kalshi affiliates and employees. Minimum payout is $1.
- A different Kalshi help page lists Sep 1 2026 as the end date, which conflicts.

**Fees and API**
- Taker fee = 0.07 × C × P × (1−P), applied to every category. Maker fees are about 0.0175 (25% of the taker fee) when a resting order fills; cancels are free. Kalshi offers full REST and WebSocket APIs — [River Markets, updated Aug 9 2026](https://www.rivermarkets.com/insights/kalshi-fees.html).
- The official fee schedule PDF, effective Feb 5 2026, lists a separate 0.0175 maker formula — [Kalshi fee schedule](https://kalshi.com/docs/kalshi-fee-schedule.pdf). This is from a search snippet only; my fetch was blocked (429 / Vercel checkpoint).
- One guide says maker fees apply only to a named list of series. Unresolved.

**International access**
- Kalshi says it is available in 140+ countries, with 38 jurisdictions restricted.
- International payment options are debit card (Visa/Mastercard), wire (minimum $1,000) and crypto.
- Kalshi is banned in Belgium, France, Singapore and Colombia, and blocked in Spain (DGOJ, May 2026). — [Kalshi help](https://help.kalshi.com/en/articles/14026044-international-access-eligibility); [SBC News](https://sbcnews.co.uk/featurednews/2025/10/14/kalshi-polymarket-growth/)

### Inferences
- Once the Volume Incentive Program ends, about Oct 13 2026, Kalshi's "volume farming" route for small traders disappears. Maker economics shift to the LIP (US-only) and to market-maker agreements.
- For a non-US operator, Kalshi offers fewer incentives than for a US one.
- Versus Polymarket international, Kalshi's 0.07 taker coefficient applies across all categories. Polymarket's ranges from 0.03 to 0.05 for sports and is 0 for geopolitics, so copying-style taker strategies are cheaper on Polymarket outside crypto.
- Polymarket US's new 0.0695 taker / 0.0125 maker-rebate schedule is now close to Kalshi's, but pays the maker instead of charging a maker fee.

### Gaps
- I could not read the official Kalshi fee PDF or the per-series maker-fee list directly.
- Total payouts under Kalshi's incentive programs were not disclosed.
- Whether the LIP end date is Jan 1 2027 or Sep 1 2026 is unresolved; the help pages conflict.
- Kalshi Market Maker Agreement terms are not public.
