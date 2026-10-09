# Systematic directional / informational edges on Polymarket (as of Oct 2026)

_STATUS: IN PROGRESS (notes written incrementally; resumed after container restart). Scratch data/scripts: /tmp/claude-0/-home-user-test/0ced0027-bcc3-524f-9ed3-ebcec6816192/scratchpad/dir/_

## Calibration / favorite-longshot bias by category (resolved markets Jun 5 - Oct 3 2026)

### Takeaway
(pending)

### Cited Findings
- Dataset: Gamma /markets/keyset closed markets with endDate on 25 sample days (every 5th day, 2026-06-05 .. 2026-10-03), ~530K markets; CLOB prices-history pulled for 27,606 binary markets with volume >= 1000 shares (stratified caps per group). Data: Polymarket public APIs (gamma-api.polymarket.com, clob.polymarket.com).

### Inferences

### Gaps


### [interim 23:15] Calibration results computed (see calib_summary.md in scratch dir)
- Logistic recalibration slope b of outcome on logit(price) (b>1 = underconfident: favourites underpriced), cluster-bootstrap by event, 95% CI:
  - POOLED non-sports non-updown: 1h before end b=1.10 [1.04,1.16]; 6h 0.99 [0.94,1.05]; 24h 0.95 [0.90,1.00]; 72h 0.92 [0.86,0.99]; 168h 1.05 [0.96,1.15].
  - finance 1h: 1.42 [1.28,1.65]; mentions 1h 1.55 [1.18,2.58], 24h 1.23 [1.02,1.55], 72h 1.44 [1.15,1.89]; tech 24h 1.39 [1.15,2.19]; weather 1h 1.10 [1.01,1.22]
  - sports_spreads 0.80 [0.64-0.97] at 1h/6h/24h pre-game (overconfident); sports moneyline ~0.95 (ns); politics ~0.92-0.99 (ns); crypto_strike ~0.9-1.07 (ns)
- Favourite band 0.90-0.98 bought at mid as maker (no fee): pooled non-sports 1h +1.7% [+0.3,+2.7] per $; 24h -1.5% [-2.8,-0.1]; 72h -1.5% [-3.1,0.0]. Mentions 24h +5.2% [+2.6,+6.8] (64 events); finance 1h +4.1% [+3.1,+4.9]; sports spreads/totals/other negative (-2 to -5%).
- Weather (11 US cities, NBS MOS from Iowa Mesonet as forecast): market Brier 0.67 vs model 0.76 (day-ahead), 0.61 vs 0.73 (same-day); in logistic y~logit(mkt)+logit(model) model coef -0.03 [-0.14,0.09] day-ahead, 0.00 [-0.09,0.10] same-day => no info beyond price. Trading model-vs-market deviations: all variants negative or CI spans 0. Open-Meteo API returned "Daily API request limit exceeded" from this container (shared IP), so not tested.
