# Polymarket Liquidity Rewards and Holding Rewards as Income Strategies ($10-50K automated trader, Oct 2026)

Data provenance: live pulls on 2026-10-09, ~22:30-23:10 UTC (read-only; no orders placed). Endpoints: CLOB `/rewards/markets/current` (18,572 rewarded markets), Gamma `/markets/keyset` (18,761 open markets with reward fields), Gamma `/events` (tags for categories), CLOB `/book` (600 books: top-300 by reward rate + 300 random others), CLOB `/prices-history` (30 days, hourly), Data API `/activity?type=REWARD` and `type=MAKER_REBATE`, Data API `/v1/leaderboard?timePeriod=MONTH`. Scripts and raw JSON are in `/tmp/claude-0/-home-user-test/0ced0027-bcc3-524f-9ed3-ebcec6816192/scratchpad/rw/` (analyze.py, net.py, net2.py, earners.py, earners_pnl.json). "[Live API]" citations below refer to those endpoints:
- [CLOB rewards](https://clob.polymarket.com/rewards/markets/current), [Gamma markets](https://gamma-api.polymarket.com/markets/keyset), [CLOB book](https://clob.polymarket.com/book), [CLOB prices-history](https://clob.polymarket.com/prices-history), [Data API activity](https://data-api.polymarket.com/activity), [Data API leaderboard](https://data-api.polymarket.com/v1/leaderboard)

## 1. What are the current rules for liquidity rewards and holding rewards (and what changed in 2025-2026)?

### Takeaway
Liquidity rewards still use the quadratic-distance scoring in the docs. Polymarket samples the book once a minute, settles each UTC day, and pays at midnight UTC with a $1 minimum. Two-sided quotes are required when the midpoint is outside 0.10-0.90; inside that range a one-sided quote scores at one third. Holding rewards pay 3.25% annualized (down from 4.00%) on the mid-marked value of positions in about 18 named long-dated events. Polymarket has said both programs are subject to change and that a "new reward and oracle-resolution system" is coming "later this year."

### Cited Findings
**Liquidity rewards: scoring and payout**
- Order score is S(v,s) = ((v−s)/v)² × b, where v is the market's max qualifying spread in cents, s is the order's distance from the size-cutoff-adjusted midpoint, and b is an "in-game multiplier". — [Polymarket docs: Liquidity Rewards](https://docs.polymarket.com/market-makers/liquidity-rewards)
- Q_one sums share-weighted scores of bids on m plus asks on the complement m′. Q_two sums asks on m plus bids on m′. When the midpoint is in [0.10, 0.90], Q_min = max(min(Q_one, Q_two), max(Q_one/c, Q_two/c)), so a one-sided quote counts at one third. When the midpoint is below 0.10 or above 0.90, Q_min = min(Q_one, Q_two), so both sides are required. The docs say c is "currently 3.0 on all markets." — [Polymarket docs](https://docs.polymarket.com/market-makers/liquidity-rewards)
- Sampling happens once per minute at a random offset, and an epoch is one UTC day (up to 1,440 samples). In each sample a maker's Q_min is divided by the sum of all makers' Q_min. These shares are summed over the day, normalized again, and multiplied by the market's daily reward. — [Polymarket docs](https://docs.polymarket.com/market-makers/liquidity-rewards)
- "Rewards are distributed directly to maker addresses daily at midnight UTC." "The minimum reward payout is $1; amounts below this will not be paid." — [Polymarket docs](https://docs.polymarket.com/market-makers/liquidity-rewards). A third-party guide adds that sub-$1 days are forfeited and do not roll over. — [startpolymarket.com reward-farming guide, updated 2026-09-15](https://startpolymarket.com/strategies/reward-farming/); [TradoxVPS, updated 2026-10-09](https://tradoxvps.com/polymarket-liquidity-rewards/)
- Each market sets its own `rewardsMinSize` (shares) and `rewardsMaxSpread` (cents). Live distribution across the 18,572 rewarded markets: max spread 4.5c in 12,632 markets, 6.5c in 3,314, 5.5c in 1,312, and 2.5c, 3.5c or 8.5c in the rest; min size 20 shares in 14,657 markets, 50 in 1,930, and 100-1,000 in a few hundred (the large-budget politics markets mostly use 150-200). — [Live API: CLOB rewards](https://clob.polymarket.com/rewards/markets/current)

**Payout token and other programs**
- Payouts are now made in pUSD, Polymarket's new collateral token, according to a 2026 guide. — [startpolymarket.com](https://startpolymarket.com/strategies/reward-farming/). The live data is consistent with this. The CLOB reward configs list asset `0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB`, while Gamma's legacy `clobRewards` field still shows USDC.e `0x2791Bca1…`. — [Live API](https://clob.polymarket.com/rewards/markets/current)
- Maker rebates are a separate program. Makers pay zero fees and receive 25% of taker fees in most fee-enabled categories, 20% in crypto and 15% in sports, paid daily with a $1 minimum. Geopolitics markets carry no fees and therefore no rebates. — [TradoxVPS](https://tradoxvps.com/polymarket-liquidity-rewards/); [startpolymarket.com](https://startpolymarket.com/strategies/reward-farming/). On-chain, rebates appear as a separate `MAKER_REBATE` activity type. — [Live API: Data API activity](https://data-api.polymarket.com/activity)
- 2026 change: in August 2026 Polymarket ran a temporary $1M reward pool for crypto 5-minute ($550K), 15-minute ($350K) and 4-hour ($100K) TWAP-settled Up/Down markets. The docs now say "This program has ended." — [Polymarket docs](https://docs.polymarket.com/market-makers/liquidity-rewards); [TradoxVPS](https://tradoxvps.com/polymarket-liquidity-rewards/). As of 2026-10-09, the live reward list has essentially nothing on Up/Down markets; all crypto-tagged rewards total $5.0K/day, mostly long-dated price-target markets. — [Live API](https://clob.polymarket.com/rewards/markets/current)
- Other 2026 changes: a V2 exchange/client migration in April-May 2026, after which Polymarket distributed the remaining liquidity rewards for the 28 April migration date — [Odaily newsflash (via search)](https://www.odaily.news/en/newsflash/479274); [KuCoin blog on V2](https://www.kucoin.com/blog/V2-launch-gives-polymarket-5-new-features?lang=en_US). There was also a move to pUSD collateral — [startpolymarket.com](https://startpolymarket.com/strategies/reward-farming/). I did not read these aggregator pages in full.

**Holding rewards**
- "we're paying 3.25% annualized Holding Reward based on your total position value in certain Polymarkets." The rate is "variable and subject to change at Polymarket's discretion," Polymarket may "introduce limits to the total amount of rewards paid out at any time," and the rewards are funded by the Polymarket Treasury. Page last modified 2026-06-01. — [Polymarket Help: Holding Rewards](https://help.polymarket.com/en/articles/13364459-holding-rewards)
- An earlier version of the same docs page (as indexed by search) said "4.00% annualized," so the rate appears to have been cut from 4.00% to 3.25% by June 2026. — [docs.polymarket.com holding-rewards (search snippet)](https://docs.polymarket.com/polymarket-learn/trading/holding-rewards), which now redirects to the help article above. The date of the cut was not found.
- Eligible events (18): Presidential Election Winner 2028; Republican and Democratic Presidential Nominee 2028; Which party wins 2028; Balance of Power: 2026 Midterms; Senate and House control in 2026; Erdoğan, Zelenskyy, Netanyahu, Xi Jinping and Putin out before 2027; Russia x Ukraine ceasefire before 2027; and the Bitcoin, Ethereum, Hyperliquid, Solana and XRP price-target events. — [Polymarket Help](https://help.polymarket.com/en/articles/13364459-holding-rewards)
- Computation: positions are valued at "the most recent mid-price for each outcome," counting both Yes and No shares. Total position value "is randomly sampled once each hour," and rewards are paid daily. Docs example: 30,000 Yes at $0.53 plus 10,000 No at $0.45 = $20,400, which earns about $0.0757/hour at 3.25%. — [Polymarket Help](https://help.polymarket.com/en/articles/13364459-holding-rewards)
- Polymarket "anticipate[s] a new reward and oracle-resolution system later this year" with "a simple 1-click migration." — [Polymarket Help](https://help.polymarket.com/en/articles/13364459-holding-rewards)

### Inferences
- The quadratic scoring strongly favors quoting close to the midpoint. At half the max spread, an order earns 0.25 of the score of an order at the mid. Most of the score sits in the inner third of the band, which is exactly where adverse selection is worst.
- The live data shows a second, small daily `REWARD` payment at about 00:15 UTC, separate from the large one at about 00:00. This is probably the holding-reward payout (see section 4), but that identification is an inference.
- Both programs can be changed or capped at Polymarket's discretion with no notice period stated, and a new system is flagged for late 2026. Any yield estimate is therefore a snapshot.

### Gaps
- The in-game multiplier b is not documented numerically. TradoxVPS also notes that b is not given for crypto markets.
- No official changelog dates were found for the 4.00% to 3.25% holding-rate cut, or for any changes to c or v in 2025-2026.
- No official statement says how sponsored rewards (`total_daily_rate` minus `native_daily_rate`; only $152/day live) differ from native rewards.

## 2. How big is the live reward budget, how is it distributed, and what yield per $ of quoted capital does it imply?

### Takeaway
About **$188K/day** (roughly $69M/yr annualized) is spread over **18,572 markets**, but very unevenly. The median market pays $3/day, the top 300 markets hold 38% of the budget, and 43 markets paying $500/day or more hold $37K/day. Ignoring fills, a small quote ($1K, two-sided) in a top-300 market grosses a median **~170% APR at the touch** or **~80% APR at half the max spread**. After a crude adverse-selection charge, the median top-300 market is **negative**. Only "slow" markets keep a positive modeled net: a median of about **+19% APR quoting at half the max spread, and +34% at the touch**. A diversified $40K book across the 20 best slow markets models at about **$60/day, or ~55% APR gross**, before adverse selection.

### Cited Findings
**Budget and distribution** (all [Live API: CLOB rewards](https://clob.polymarket.com/rewards/markets/current) + [Gamma](https://gamma-api.polymarket.com/markets/keyset), pulled 2026-10-09)
- Total `total_daily_rate` across the 18,572 markets is **$188,404/day**. Of this, $188,252 is native and $152 is sponsored.
- Concentration: the top 10 markets hold 9.8% of the budget, the top 50 hold 20.8% (the 50th market pays $300/day), the top 100 hold 26.6% ($200/day at rank 100), the top 300 hold 38.4% ($84/day at rank 300), the top 1,000 hold 57.5% ($41/day), and the top 3,000 hold 77.3% ($10/day). The median market pays **$3/day**.
- Markets by daily rate:

  | Daily rate | Markets | Budget |
  |---|---|---|
  | <$1 | 288 | ~$0 |
  | $1-10 | 15,127 | $41.2K/day |
  | $10-50 | 2,286 | $44.7K/day |
  | $50-100 | 604 | $33.1K/day |
  | $100-500 | 224 | $32.4K/day |
  | ≥$500 | 43 | $36.9K/day |

- By category (event tags; first match wins, so Fed and data-center markets fall under Politics):

  | Category | Markets | Budget | Share |
  |---|---|---|---|
  | Politics/Elections | 5,165 | $84.3K/day | 44.8% |
  | Sports | 8,104 | $37.3K/day | 19.8% |
  | Weather | 713 | $19.4K/day | 10.3% |
  | Tech/AI | 1,084 | $16.0K/day | 8.5% |
  | Finance/Economy | 1,398 | $14.7K/day | 7.8% |
  | Culture | 577 | $6.8K/day | 3.6% |
  | Crypto | 1,124 | $5.0K/day | 2.7% |
  | Geopolitics | 342 | $4.3K/day | 2.3% |

  No 5/15-minute Up/Down markets carry rewards.
- By fee schedule: $87.6K/day of rewards sits in markets with a 4% taker fee and 25% rebate, $38.2K/day at 5%/25%, $29.3K/day at 5%/15% (sports), and $21.3K/day in fee-free markets. Most rewarded markets therefore also pay maker rebates on fills.
- The single largest budgets:

  | Market(s) | Daily rate | Max spread | Min size |
  |---|---|---|---|
  | "US x Iran ceasefire continues through Oct 12" | $4,000 | 4.5c | 200 |
  | Same, Oct 15 | $2,025 | 4.5c | 200 |
  | "North Carolina enacts data center moratorium" (4 markets) | ~$2,000 each, $8.0K total | 4.5c | 50 |
  | "2026 Balance of Power: D Senate, D House" | $1,331 | — | — |
  | Brazil election (Bolsonaro, Lula) | ~$1,000 each | — | — |
  | Fed October decision | ~$1,000 per outcome | 2.5c | — |
  | Data-center moratorium markets in 7 other states (each with 4 date markets) | $500 per market | — | — |
  | Anthropic/OpenAI/CoreWeave/NuScale/Payward bankruptcy ladders | $100-$500 per market | — | — |

  The Brazil election markets ended 2026-10-05 but were still listed.

**Yield model** (books: [CLOB /book](https://clob.polymarket.com/book); price paths: [CLOB /prices-history](https://clob.polymarket.com/prices-history))
- Method:
  - For each book I computed the competing score from all resting size meeting min size and within v of the size-adjusted mid, applying Q_min to the aggregate book.
  - I then added a hypothetical symmetric two-sided quote of N=1,000 shares per side, which ties up roughly $1,000 of collateral because a YES bid plus a NO bid cost about $1 per pair. Two placements were tested: the best bid/ask ("touch") and half the max spread (score factor 0.25).
  - APR = daily rate × my share × 365 / $1,000.
  - Caveats: treating the aggregate book as a single maker misstates competition. The prior run's aggregation over-counts competition by a median of ~12% against the exact doc formula, so the APRs below are slightly conservative. The calculation also assumes the snapshot depth persists all day.
- Gross APR (no fills), 230 of the top-300 markets with usable books and history: touch **p25 56% / median 169% / p75 535%**; half-spread **23% / 81% / 364%**. Random sample of 275 other markets: touch median 34%, half-spread median 52%.
- Adverse-selection proxy: the loss to a static quote, measured as daily price moves beyond the quote's distance times quote size. This is a crude proxy, not a backtest; the hourly version gives losses 2-3 times higher.
  - Top-300 net: touch median **−138%**, half-spread median **−66%**. Only 34% (touch) and 40% (half) of top-300 markets come out net-positive. Random sample: net-positive in only 6%/11%.
  - Category medians of the hourly proxy are all deeply negative except weather (n=5).
- "**Slow**" markets, defined as a 30-day price range ≤ 2× max spread: 63 of 230 top-300 markets, carrying **$16.1K/day of the $62.9K/day** top-300 budget.
  - Gross: touch median 75%, half-spread 22%.
  - Daily-proxy loss: touch median 30%, half-spread **0%**.
  - **Net: touch median +34% (68% of markets positive); half-spread median +19% (86% positive), p75 +68%.**
- Best long-dated, slow, reasonably deep markets (half-spread quote, net of daily proxy):

  | Market | Rate | Mid | Competing score (shares) | Half-spread gross | Touch gross |
  |---|---|---|---|---|---|
  | TX-36 House seat (Dem) | $100/d | 0.059 | 6.0K | 145% | 481% |
  | FL-03 House seat (Dem) | $100/d | 0.058 | 8.2K | 108% | — |
  | Climate Clock 1.5°C deadline | $50/d | 0.065 | 4.4K | 97% | — |
  | NC data-center moratorium by Dec 2028 | $2,000/d | 0.255 | 201K | 91% | — |
  | NC moratorium by Dec 2026 | $2,004/d | 0.055 | 268K | 68% | 215% |
  | NC moratorium by June 2027 | $2,002/d | 0.155 | 282K | 65% | 204% |
  | KS-04 / MN-06 / FL-17 / TX-04 / SC-07 House seats | — | — | — | 48-67% | — |
  | Payward bankruptcy 2028 | $200/d | — | — | 35% | — |
  | U.S. invade Iran before 2027 | $400/d | — | — | 21% | — |
  | Marine Le Pen 2027 | $259/d | — | 93K | 25% | — |

  The NC June 2027 market's 30-day range was only 0.5c.
- Portfolio sizing check: $2K in each of the top 20 slow markets (ending after 2026-10-20, competing score >2K shares), quoted at half the max spread, gives **~$60/day on $40K = ~55% APR gross** before fills. At $5K at the touch, the NC moratorium markets model at ~200% gross ("top5k" column), so large budgets keep yield at size, whereas the $100/day House-seat markets saturate quickly.
- Fast markets are traps:
  - The highest gross yields (thousands of % APR) are in thin, news-driven markets: MrBeast view-count brackets, "Next Fable model released by Oct 10," "Gemini 4.0 by Oct 15," WTI $100 in October, the Romanian PM, the Talarico-Paxton debate.
  - Their 30-day ranges are 30-68c, and the modeled adverse-selection losses run 10-260 times the gross reward.
  - The Iran-ceasefire date ladder ($4K + $2K + $1K + $1K + $500 + $300/day) shows very high gross yield (1,000-2,700% at the touch) but resolves on single geopolitical headlines.

### Inferences
- The reward budget is real and large, but the attractive part for a small operator is narrow. Roughly $10-20K/day of budget sits in markets that are both well funded and slow. Within it, a $10-50K operator quoting at half to two-thirds of the max spread could plausibly gross 30-60% APR and net perhaps **15-30% APR** after realistic adverse selection. That net range is a judgment informed by the earner P&L data in section 3, not a measured result.
- Yield on deep, high-budget markets (NC/state data-center moratoria at $500-$2,000/day per market with 100-300K competing shares) degrades slowly with size, so they suit $20-50K. The $100/day House-seat markets offer the best ratio but only absorb a few thousand dollars each.
- Low-probability markets (mid <0.10) require two-sided quotes. The NO-side bid near $0.94 ties up almost $1 per share, while the YES bid costs pennies. A fill on the NO side is a cheap-looking position that can go to zero on resolution or news.

### Gaps
- No minute-level sampling of competing depth over a full epoch was done; one snapshot per market was used.
- The fill model is a proxy based only on hourly or daily midpoints. It ignores maker rebates earned on fills (which would partly offset losses) and does not model cancel-on-move logic, which practitioners use to cut adverse selection.
- I could not identify which wallets were quoting in a given market from the anonymized book; the earner analysis below is wallet-level, not per-market.

## 3. Who actually earns rewards, what do they net after trading losses, and what are the main risks? How does this compare with maker-rebate MM in 5/15-min crypto Up/Down?

### Takeaway
Rewards are concentrated among a few dozen professional farmers. Among 171 wallets that were top traders in the 60 largest-budget markets, the top 10 each collected **$42K-$132K in 30 days**. Their trading P&L, however, typically gives back about half of the rewards: the median ratio of trading loss to rewards-plus-rebates is 0.47, rising to 0.70 among those with negative trading P&L. Still, 31 of the 40 biggest earners were net positive over the month. That evidence supports reward farming in slow markets as a better risk-adjusted use of $10-50K than maker-rebate MM in crypto Up/Down. In Up/Down markets, rebates (~0.42% of fills) are smaller than adverse selection (~0.50%) for all but the top ~200 wallets, and the crypto TWAP reward pool has ended.

### Cited Findings
**Earner data** ([Live API: Data API activity](https://data-api.polymarket.com/activity) type=REWARD/MAKER_REBATE; [Data API leaderboard](https://data-api.polymarket.com/v1/leaderboard) timePeriod=MONTH)
- Sample: 171 wallets, the top-6 traders by trade count in each of the 60 largest-budget markets.
  - 147 received rewards in the last 30 days, totaling **$1.12M/30d (~$37K/day, about 20% of the global budget)**.
  - Median earner: $502/30d.
  - Distribution: 24 wallets earned <$1, 25 earned $1-100, 51 earned $100-1K, 45 earned $1-10K, and 26 earned more than $10K.
- Top earners, 30-day rewards / maker rebates / leaderboard monthly trading P&L / volume:

  | Wallet | Rewards | Rebates | Trading P&L | Volume |
  |---|---|---|---|---|
  | Haradwaith | $132.2K | $13.7K | **−$238.3K** | $11.9M |
  | tradetosurvive1 | $115.8K | $7.1K | −$89.0K | $3.0M |
  | sdfsdfsdfsdf2 | $73.6K | $1.8K | −$45.5K | $3.0M |
  | AJSV | $61.5K | $6.7K | +$173.0K | $6.9M |
  | lolzzzlol | $60.4K | $2.5K | −$54.9K | $2.3M |
  | WarriorH | $50.9K | $5.8K | +$63.9K | $8.7M |
  | GuyFromTinder | $46.7K | $2.1K | −$37.3K | $1.4M |
  | ArmageddonRewardsBilly | $41.8K | $4.6K | +$526.4K | $6.4M |

  Pure farmers (tradetosurvive1, sdfsdfsdfsdf2, lolzzzlol, GuyFromTinder, 0x49F206, Digital-Boy) gave back 60-120% of their rewards in trading P&L.
- Across the top 40 earners ($1.03M rewards, $170K rebates), **27/40 had negative monthly trading P&L**. The median ratio of trading loss to (rewards + rebates) was 0.47 overall and 0.70 among the losers. **31/40 were net positive** (rewards + rebates + P&L), with a median net of +$8.3K for the month.
- Payout pattern: top earners receive two `REWARD` payments every day, a large one at ~00:00-00:05 UTC (e.g. Haradwaith $3.4-4.5K/day) and a small one at ~00:15 UTC ($3-23/day), plus a separate daily `MAKER_REBATE`.
- Some top farmers show tiny positions value against large rewards (e.g. sdfsdfsdfsdf2 at $5.9K, rubby1337 at $1K, SPLPB at $1.7K). Positions value excludes cash and order collateral, so it cannot be used as an APR denominator. This is consistent with farmers keeping inventory near flat.

**Practitioner and third-party reports**
- "Elton earns thousands of dollars a day in liquidity rewards, but also has $100K+ PNL swings"; he "trades an inhuman 1000+ markets a day." "$1,331 in rewards will place you in the top 1% of polymarket traders" (citing Polyrewards stats). Suggested tactics include quoting far from the mid and cancelling "when the price moves towards your quote," and seeking "oddball/annoying markets with large rewards." — [EventWaves Substack, 2026-05-20](https://eventwaves.substack.com/p/how-to-farm-liquidity-rewards-on)
- A third-party guide counts ~7,300 concurrently rewarded markets sharing ~$200K/day with a median of ~$5/day. A vendor guide projects $2-15/day on $1-5K, which should be treated as marketing. — [WebSearch summary of startpolymarket.com / laikalabs.ai / polymarkets.co.il](https://startpolymarket.com/strategies/reward-farming/). My live count is higher (18,572 markets, median $3/day), possibly because the guide predates new low-rate markets.
- The startpolymarket.com guide gives a risk example: a 53c bid on 100 shares with fair value falling to 2c loses $51, more than a $50/day reward. It also lists resolution risk, competition dilution, stale quotes and capital lock-up. — [startpolymarket.com, 2026-09-15](https://startpolymarket.com/strategies/reward-farming/)
- The open-source poly-maker bot (warproxxx) states: "Market making on Polymarket is competitive and can lose money"; it is "a reference implementation and a research harness, not a guaranteed-profitable product." Its selector "ranks them by reward + rebate income vs. volatility/spread risk" and keeps quotes "inside the liquidity-rewards band in QUIET" regimes. — [poly-maker README](https://raw.githubusercontent.com/warproxxx/poly-maker/main/README.md). A search summary puts its last push at 2026-04-06, with ~1.1K stars. — [gittrend.io](https://gittrend.io/repo/warproxxx/poly-maker)
- Comparison baseline for crypto Up/Down maker-rebate MM, from the coordinator's prior internal analysis (not re-verified here): rebate ≈0.42% of filled notional against ≈0.50% adverse selection, with only the top ~200 maker wallets profitable. The $1M August-2026 TWAP reward pool for those markets has ended. — [Polymarket docs](https://docs.polymarket.com/market-makers/liquidity-rewards)

### Inferences
- **Risk-adjusted comparison.** Reward farming in slow, long-dated markets earns income per unit of time, whether or not orders fill. Up/Down rebate MM earns only on fills, and those fills are exactly the adversely selected flow. That gives reward farming a structurally better risk/return profile for a $10-50K operator. The best-funded farmers still lose most of their rewards in trading where they quote fast or newsy markets (Haradwaith is net −$92K), so market selection and cancel-on-move logic drive the outcome.
- **Main risks.**
  - Jump risk on news: ceasefire, legislative and AI-release markets can move 20-60c in minutes.
  - Resolution-date jumps: the House-seat markets resolve 2026-11-04, so quotes must be pulled before results.
  - Inventory that ends up on the losing side of a binary outcome.
  - Collateral locked in quotes. The capital earns nothing except the reward, and holding reward only if inventory sits in an eligible event.
  - Program risk: budgets are set per market and can be cut overnight; the holding rate has already fallen from 4.00% to 3.25%.
  - Competition: large farmers add depth to the best ratio markets quickly.
  - Operational: the 1/min random sampling means quotes must be continuously present, and the $1/day/market minimum makes many tiny markets unpayable for small size.
  - Jurisdiction: this container is US-geoblocked for trading.
- **Realistic expectation for $10-50K.** Gross 30-60% APR in slow markets, with roughly 30-70% of gross lost to adverse selection based on the earner data, gives a net of roughly 10-30% APR, with fat left tails around news events. On $25K that is very roughly $7-20/day. This is an estimate, not a measured result.

### Gaps
- Leaderboard monthly "pnl" definition: I could not confirm whether it is mark-to-market including unrealized, or whether it excludes rewards. I assumed it is trading P&L excluding rewards, because adding rewards turns most of the top earners net positive, which looks plausible. If P&L already includes rewards, farmer economics are much worse.
- The earner sample is biased toward the highest-volume wallets in the biggest-budget markets. Small quiet farmers in slow markets are under-sampled.
- No Dune dashboard or X/Twitter thread with audited small-account farming returns was found. Polyrewards stats is cited by EventWaves but was not accessed.

## 4. Holding rewards: which markets, how much capital is eligible, and what is the effective APY against price risk?

### Takeaway
Holding rewards pay **3.25% APY** on the mid-marked value of positions in **339 markets across 41 Gamma events**. These correspond to about 18 eligible event families plus some legacy or expanded ones. They hold about **$130M of open interest**, which implies roughly **$4.2M/yr (~$11.6K/day)** of treasury cost if fully paid. On its own, a directional position earning 3.25% is negligible against price risk. The docs count both Yes and No shares, so a near-delta-neutral **full set (Yes+No) in an eligible market appears to earn ~3.25% on idle collateral**. That is a modest but almost price-risk-free complement, useful for parking reward-farming inventory.

### Cited Findings
- 339 open markets have `holdingRewardsEnabled=true`, grouped into 41 events. — [Live API: Gamma](https://gamma-api.polymarket.com/markets/keyset)
- Largest eligible events by open interest:

  | Event | Open interest | LP reward |
  |---|---|---|
  | Presidential Election Winner 2028 | $43.4M | $100/d |
  | Bitcoin price 2026 | $13.6M | ~$0 |
  | Balance of Power 2026 | $11.6M | $2.5K/d |
  | Democratic Nominee 2028 | $9.8M | — |
  | Republican Nominee 2028 | $9.5M | — |
  | Putin out | $7.7M | — |
  | House 2026 | $6.6M | $500/d |
  | China invades Taiwan 2026 | $6.1M | — |
  | Ethereum price 2026 | $6.0M | — |
  | Xi out before 2027 | $4.2M | — |
  | Senate 2026 | $2.3M | $1K/d |
  | Indiana data-center moratorium | $1.5M | $2K/d |

  Total eligible OI is **~$130.1M**, so 3.25% implies about **$4.23M/yr**. — [Live API: Gamma events openInterest](https://gamma-api.polymarket.com/events)
- Live flags show eligibility has expanded beyond the help article's list of 18. The data-center moratorium ladders (Indiana, NC, Louisiana, Missouri, Oklahoma, Texas, Ohio) and the Anthropic/OpenAI/CoreWeave/NuScale/Payward bankruptcy ladders are all flagged, and these also carry large LP budgets ($300-$8,006/day per event). Also flagged: Trump impeachment, the Maxwell pardon, and state-senate control events. — [Live API: Gamma](https://gamma-api.polymarket.com/markets/keyset) versus [Polymarket Help list](https://help.polymarket.com/en/articles/13364459-holding-rewards)
- Rate: 3.25%, variable, with possible caps, after being 4.00% earlier. — [Polymarket Help](https://help.polymarket.com/en/articles/13364459-holding-rewards); [earlier docs snippet](https://docs.polymarket.com/polymarket-learn/trading/holding-rewards)
- Valuation counts both Yes and No shares at mid, sampled randomly once an hour. The docs example holds both sides. — [Polymarket Help](https://help.polymarket.com/en/articles/13364459-holding-rewards)
- Observed: the small ~00:15 UTC daily `REWARD` entries on farmer wallets ($1-23/day) are consistent in size with 3.25% on tens to a few hundred thousand dollars of eligible inventory. — [Live API: Data API activity](https://data-api.polymarket.com/activity) (the identification is an inference)

### Inferences
- **Directional holding.** 3.25% APY is dwarfed by price risk. A 30-day range of even 3-5c on a 25c contract is a 12-20% move. Holding rewards should not drive directional positions.
- **Full-set holding.** Minting or holding a Yes+No pair is worth about $1 at mid and earns ~3.25% with almost no price risk. Residual risks are mid-vs-$1 drift, smart-contract/pUSD/platform risk, the possibility that Polymarket caps or excludes this, and program termination with the announced "new reward system." On $10-50K that is about $325-1,625/yr. It is useful as a floor yield on idle collateral, or on reward-farm fill inventory that has been merged or paired, but it is not an income strategy by itself.
- **Synergy.** Several of the best slow LP markets (the NC, Indiana and other data-center moratorium ladders; the bankruptcy ladders; Balance of Power) are also holding-eligible. Inventory accumulated from fills there earns 3.25% on top of LP rewards, which slightly reduces the carrying cost of inventory risk.

### Gaps
- I found no confirmation that Polymarket allows or pays on hedged full sets beyond the docs' Yes+No example, and no statement of any per-user cap.
- I could not determine the effective date of the 4.00% to 3.25% cut, or what the announced "new reward and oracle-resolution system" will change.
- Gamma's `openInterest` is event-level. Whether every eligible dollar is actually paid, given caps, is unknown.
