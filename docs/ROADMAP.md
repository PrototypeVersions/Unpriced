# UNPRICED Roadmap

This roadmap separates the current champion system from future challengers. Dates are evidence checkpoints, not promises to promote a new model.

## Stage 0 — V1 launch and integrity period

**Target:** first ~20 trading days.

V1 should run prospectively without performance-driven redesign. Fix genuine software, scheduling, or data-integrity bugs when necessary, but do not tune model logic because of ordinary wins/losses.

Primary checks:

- immutable close snapshots are written correctly;
- 1D/5D/20D resolutions line up with exchange sessions;
- calibration/scoring code is correct;
- paper execution follows precommitted rules;
- provider failures are exposed rather than hidden;
- site and repo remain synchronized.

## Stage 1 — Begin V2 challenger development

**Checkpoint:** around ~20 trading days of V1 operation.

V2 should be developed as a separate challenger. It may use V1's accumulated record diagnostically, but should not be optimized to explain away a few recent misses. Once V2's methodology is frozen, it should begin issuing its own prospective shadow forecasts.

Likely V2 directions:

1. **Better point-in-time market data** — preferably a licensed/reliable daily + intraday provider.
2. **Expectation data** — analyst estimate levels and revisions, earnings expectations, and changes in consensus.
3. **Event semantics** — structured information from earnings releases, filings, guidance, and other disclosures with strict timestamp/provenance handling.
4. **Economic relationship graph** — supplier/customer/competitor/industry exposure rather than V1's return-correlation-only propagation layer.
5. **Richer propagation logic** — distinguish leader information shocks from lagger non-adjustment, with causal claims kept separate from empirical association.

V2 should not control the official V1 $1,000 portfolio during its shadow period.

## Stage 2 — First serious V1 vs V2 comparison

**Checkpoint:** roughly ~60 trading days of V1 history, assuming V2 has accumulated a meaningful shadow record.

Compare at least:

- Brier score;
- log loss;
- calibration curves/bins;
- Spearman rank IC;
- performance by forecast horizon;
- performance by forecast date, not only ticker observation;
- performance across market regimes;
- model agreement/disagreement behavior;
- turnover and estimated costs;
- shadow portfolio economics versus V1 and SPY.

No single metric should decide the winner.

## Stage 3 — Promotion eligibility

**Window:** roughly 60–90 trading days, only if the prospective challenger record is sufficiently informative.

A challenger becomes eligible for champion promotion only if it shows a durable advantage on prospective data and does not introduce a serious calibration, robustness, data-quality, or turnover weakness.

Promotion should be an explicit versioned event. V1's historical record remains V1's record forever.

## Stage 4 — Later research directions

Potential later versions/challengers include:

- options-implied information (volatility surface, skew, term structure, unusual repricing);
- model competence maps that learn which model families are strongest for which names/regimes/horizons;
- regime-specific ensembles under precommitted rules;
- richer causal/economic networks for propagation;
- event-specific models for earnings, guidance, filings, macro releases, and sector shocks;
- uncertainty decomposition and provenance/explanation layers;
- broader but carefully controlled asset universes;
- a separate intraday challenger that reacts at fixed later windows without modifying the original daily experiment;
- parallel Conservative/Core/Aggressive paper portfolios while preserving a single official forecast record;
- formal champion/challenger dashboards showing prospective head-to-head evidence and promotion eligibility.

## What should *not* happen

- V1 should not be retroactively changed because V2 looks better.
- V2 should not receive credit for forecasts made before V2 existed.
- A backtest should not substitute for a shadow forward period.
- New data sources should not silently rewrite old feature values, forecasts, or fills.
- Promotion should not be based on one unusually profitable trade or one favorable market regime.

<!-- AUTO-SNAPSHOT:START -->
## Automated current snapshot

_Generated from `config.json`, `data/system.json`, and immutable files under `forecasts/`. Do not hand-edit this block._

- **System status:** `live`; phase `live-forward-experiment`; live since: 2026-11-02T20:11:56.438996-05:00.
- **Last successful cycle:** 2026-11-12T18:49:33.556080-05:00; **last recorded error:** none.
- **Forward record:** 9 immutable close snapshots; 1080 official forecast observations; 480 resolved live observations.
- **V2 development checkpoint:** not yet reached (9/20 immutable close snapshots).
- **Adaptive ensemble status:** eligible (480/100 resolved live predictions).
- **Official schedule (America/New_York):** premarket 08:45; paper execution 09:35; normal close 16:35; early close 13:35.
- **Forecast target:** relative to `SPY` at 1, 5, 20 trading-session horizons; website display minimum 55.0%.
- **Portfolio gates:** entry probability ≥ 60.0%; exit probability ≤ 52.0%; expected excess-return entry floor 0.4%.
- **Portfolio:** starting cash $1,000; max 4 positions; max position weight 22.5%; cost/slippage 0.1% per side; overnight new-entry veto 4.0% absolute gap.
- **Learning:** rolling 3-year training window; initial weights `broad_logit` 45.0%, `boosted` 35.0%, `momentum_logit` 20.0%; adaptive lookback up to 250 resolved live predictions; weight floor 10.0%; cap 70.0%.
- **Coverage:** 40 forecast-universe equities plus 10 market/context symbols.
- **Data adapter:** `yfinance-research-prototype`; fail closed: `True`.
<!-- AUTO-SNAPSHOT:END -->
## Updating this roadmap

The automated block above tracks mechanically knowable progress. The narrative roadmap is intentionally not auto-rewritten by code. When a substantive new direction is approved, update this file, `docs/DECISIONS.md`, and `docs/CHANGELOG.md` together.
