# UNPRICED Operations Guide

UNPRICED is designed to run without routine human intervention. This file defines what should be monitored and when manual attention is actually warranted.

## Normal daily sequence (America/New_York)

- 08:45 — premarket refresh; may veto planned entries but never rewrites published probabilities.
- 09:35 — paper execution using the completed first five-minute bar.
- 16:35 — official close cycle; resolves matured forecasts, retrains model parameters, freezes new 1D/5D/20D forecasts, updates market state and propagation, and writes the forward record.
- Early-close sessions use 13:35 for the official close cycle.

## Scheduler reliability and late-run safety (repaired 2026-11-03)

GitHub Actions weekday cron schedules remain the primary autonomous updater, with redundant
premarket (08:45, 08:53 ET), execution (09:35, 09:42 ET), early-close (13:35, 13:49 ET),
and normal-close/recovery (16:35, 16:47, 17:07, 17:37, 18:07 ET) triggers.
They are not guaranteed to start exactly on time. The actual NYSE calendar and engine
clock, not the scheduled cron text, decide which work is allowed.

- A premarket job that arrives after the 09:30 open records a missed-run audit and
  does not create retrospective risk eligibility.
- A paper-execution job may execute only from 09:35 through 09:45 ET. Missed windows
  are recorded separately, without simulated fills, benchmark starts, or backdating.
  An existing dated execution prevents a second run for the session.
- A timely execution requires a previous-session official forecast and a same-session
  premarket risk check for any **new entry**. No unfinished 09:35 candle may substitute
  for the completed 09:30–09:35 bar.
- Official close publication requires a genuinely current-session SPY daily bar;
  missing current-session feature rows are rejected instead of silently replaced with
  a prior session. Subsequent close retries no-op after the first immutable snapshot.
- Code-repair pushes to the market-cycle workflow can initiate a current-day close
  recovery **only** after the session closes, preserving the actual publication time.
- Each successful market-cycle run synchronizes generated documentation before
  pushing state, and the public page polls for published data while visible.
- A skipped late cycle is an operational miss, not a successful timely cycle.
  Inspect `states/*-missed.json` even if GitHub marks the job green.

### November 11, 2026: confirmed schedule-latency incident

The Actions API and job logs show that a successful workflow run did **not**
constitute timely market execution. On November 11, the scheduled paper-execution
job in [run 43103719295](https://github.com/PrototypeVersions/Unpriced/actions/runs/43103719295)
started at **16:31:01 ET** (21:31:01 UTC), outside the permitted 09:35–09:45 ET
window. The job recorded an execution miss, not a fill. The scheduled close cycle in
[run 43131061398](https://github.com/PrototypeVersions/Unpriced/actions/runs/43131061398)
was created at **19:57:21 ET** (00:57:21 UTC November 12) and published the
November 11 immutable snapshot at **19:58:01 ET**, well after the 16:35 target.
The Pages deployment succeeded in that run. Delays occurred before run creation,
not primarily during the engine itself; GitHub documents that cron events are
best effort and may be delayed or dropped. Redundant cron triggers cannot
guarantee exchange-time deadlines.

The operational-only `scripts/audit_session.py` now runs after the engine and before
state validation/commit. It reports actual NYSE-relative outcomes as Actions
step summaries and warnings. If no valid same-session premarket or execution
record exists after its cutoff, it creates a timestamped
`states/YYYY-MM-DD-*-missed.json` without changing any existing record.
Regression checks in `tests/smoke.py` cover idempotency, avoiding a fabricated
premature miss, and preserving the close+35-minute settlement boundary.
This audit does not make delayed GitHub schedule events punctual.

Reliable 08:45/09:35/16:35 ET timing requires an independent authenticated
scheduler to dispatch this existing workflow with `mode=premarket`,
`mode=execute`, or `mode=close` (13:35 for NYSE early closes), retaining native
GitHub cron as a fail-closed fallback. The `workflow_dispatch` inputs already
support those modes. An external scheduler requires one-time owner authorization;
no external service or token has been configured without that action.

The 2026-11-03 execution was hours late and placed zero trades. Its unchanged original
state is accompanied by `states/2026-11-03-execution-audit.json`; the mutable SPY
benchmark start was reset, pending the next valid forward-time execution. No trade
or forecast history was rewritten.

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
