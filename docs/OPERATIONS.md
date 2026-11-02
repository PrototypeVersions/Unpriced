# UNPRICED Operations Guide

UNPRICED is designed to run without routine human intervention. This file defines what should be monitored and when manual attention is actually warranted.

## Normal daily sequence (America/New_York)

- 08:45 — premarket refresh; may veto planned entries but never rewrites published probabilities.
- 09:35 — paper execution using the completed first five-minute bar.
- 16:35 — official close cycle; resolves matured forecasts, retrains model parameters, freezes new 1D/5D/20D forecasts, updates market state and propagation, and writes the forward record.
- Early-close sessions use 13:35 for the official close cycle.

## What counts as healthy

A healthy trading day should normally produce:

1. a successful `UNPRICED Market Cycle` premarket run;
2. a successful execution run (which may legitimately place zero trades);
3. a successful post-close run;
4. a dated immutable forecast file under `forecasts/` after the close cycle;
5. updated `data/system.json`, `data/current-forecasts.json`, `data/model-state.json`, and `data/track-record.json`;
6. a successful validation workflow after bot commits;
7. a Pages deployment when GitHub Pages is enabled.

Zero trades, zero propagation gaps, or few displayed forecasts are not failures. The system is explicitly allowed to find no sufficiently strong opportunity.

## Conditions that require attention

Manual review is warranted when any of the following persists beyond one trading session:

- scheduled market-cycle workflow failure;
- no new close snapshot on a normal trading day;
- `data/system.json` contains a non-null `lastError`;
- the public site is more than one trading day behind the repository;
- repeated market-data failures or missing symbols;
- forecast count collapses unexpectedly because the data universe is unavailable;
- portfolio execution is repeatedly skipped because 5-minute data are unavailable;
- a validation workflow fails after an automated market-cycle commit.

One isolated provider or GitHub scheduling failure is not grounds to alter the model or history. Missed cycles remain missed rather than being retrospectively backfilled as live forecasts.

## Data-provider policy

V1 uses `yfinance` as a research-grade, credential-free prototype adapter. It may become stale, change behavior, throttle requests, or fail. UNPRICED therefore fails closed rather than fabricating data.

The highest-priority infrastructure upgrade, once the experiment proves worth continuing, is a licensed point-in-time market-data provider with reliable daily and intraday bars. Changing providers must be versioned and may not rewrite old forecasts or fills.

## Learning policy

- Model parameters retrain automatically after each valid close using the rolling historical window.
- Ensemble weights remain fixed until at least 100 genuinely live resolved predictions exist.
- After that threshold, weights adapt only from live out-of-sample Brier performance under the frozen floors/caps/lookback rules.
- Architecture and source code do not self-modify.
- New model families enter as explicit challengers/new versions and cannot take credit for forecasts made before they existed.

## Suggested review cadence

### After the first trading day
Verify that the first post-close forecast snapshot exists and the site displays it correctly.

### After the first 5 trading days
Check that 1-day forecasts are resolving correctly and that the portfolio's execution records match the precommitted rules.

### After ~20 trading days
Review preliminary calibration, directional performance, rank IC, and portfolio-vs-SPY results, but do not tune the strategy from such a small sample unless there is a software/data bug.

### After 100+ resolved predictions
The adaptive ensemble may begin changing weights automatically. Verify that the weight history is sensible and that no model is dominating because of a data or scoring error.

### Monthly
Review data quality, provider failures, coverage of the stock universe, model-family performance, calibration, turnover/costs, and whether a challenger model deserves to be tested. Do not alter historical records.

## Do not react to

- a few losing trades;
- a bad week;
- one model having a short losing streak;
- the portfolio underperforming SPY briefly;
- a day with no trades;
- a day with no strong propagation gap.

The experiment becomes useful only if its rules survive ordinary bad outcomes without discretionary hindsight changes.
