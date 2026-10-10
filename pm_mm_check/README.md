# pm_mm_check: is Polymarket market making viable?

Scripts that test the "market making on Polymarket for maker rebates" thesis against Polymarket's public APIs.
No API key or account is needed. **Findings: [REPORT.md](REPORT.md).**

```bash
cd pm_mm_check
pip install -r requirements.txt
python claims_check.py                                   # fee formula on a live market + geoblock for your IP
python fee_census.py                                     # fee schedules of all markets, 24h fees, rebate pool size (~7 min)
python maker_pnl_backtest.py --lookback 15m:168,5m:48,4h:336   # maker P&L in resolved crypto Up/Down markets
python competition.py --lookback 15m:48,5m:48,4h:48     # maker wallets: concentration and who profits
python orderbook_snapshot.py --snapshots 8 --every 20    # live spreads and depth
# liquidity-reward farming follow-up (see REWARD_FARMING_VALIDATION.md)
python leaderboard_reward_check.py 0xWALLET ...          # does leaderboard P&L include rewards? (it doesn't)
python reward_farming_replay.py --days 30 --min-rate 50 # 30-day fill/reward replay of a quoting bot (~1h)
python reward_replay_summary.py --date YYYYMMDD          # full-window, out-of-sample summary
python reward_jump_stress.py --date YYYYMMDD             # worst-case informed-sweep stress
```

Outputs go to `results/` (CSV/JSON, dated). Immutable API responses for closed markets are cached in `.cache/`, so
re-runs are fast.

| File | What it does |
|---|---|
| `pm_api.py` | Thin client (retries, disk cache) for Gamma, Data-API and CLOB, plus the fee formula |
| `claims_check.py` | Recomputes "$1.75 per 100 shares at $0.50", the fee/rebate % by price, and geoblock status |
| `fee_census.py` | Taker fees and rebate pool by fee type, estimated two independent ways |
| `maker_pnl_backtest.py` | Every taker fill seen from the maker side: rebate vs adverse selection, with window-clustered bootstrap CIs |
| `competition.py` | Attributes maker fills to wallets: concentration, P&L by volume tier |
| `orderbook_snapshot.py` | Spread, top-of-book size and depth of the currently trading Up/Down books |
