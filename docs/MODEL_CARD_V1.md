# UNPRICED V1 Model Card

## Scope

UNPRICED V1 is the initial prospective champion system. It produces relative-performance forecasts versus SPY over 1, 5, and 20 trading sessions and feeds a separate $1,000 paper-trading experiment.

## Prediction target

For ticker `i`, forecast date `t`, and horizon `h`:

`excess_return(i,t,h) = return(i,t→t+h) - return(SPY,t→t+h)`

The directional event is whether excess return is positive.

## Model families

### broad_logit

Interpretable logistic model over standardized point-in-time features including short/medium momentum, one-day reversal, realized volatility, volume surprise, relative strength, and market-state features.

### boosted

Histogram gradient-boosted classifier using the same broad information set to capture nonlinear interactions.

### momentum_logit

Narrow relative-momentum logistic specialist included as a deliberately simple benchmark.

### expected excess-return model

A regression layer estimates expected relative return for ranking and portfolio filtering. Directional probability and expected excess return are tracked separately.

## Representative V1 feature families

- 1D return / reversal;
- 5D, 20D, 60D momentum;
- 5D, 20D, 60D relative momentum versus SPY;
- 20D realized volatility;
- volatility ratio;
- 20D standardized volume surprise;
- SPY trend and volatility;
- market breadth;
- cross-sectional dispersion.

Features must be computed only from information available at the publication boundary.

## Retraining and ensemble learning

Model parameters retrain after valid close cycles using a rolling three-year historical window. This is routine parameter learning, not source-code self-modification.

Initial ensemble weights are frozen. Live-performance adaptation is prohibited until the configured minimum number of genuinely live resolved observations exists. After that, component weights may adapt using recent live Brier performance under fixed lookback, temperature, floor, and cap settings.

Historical/backtest rows do not enter the live adaptive score as though they were prospective observations.

## Forecast publication

Official forecasts are frozen once per trading day after the close. Each dated snapshot stores the publication timestamp, horizon, probability, direction, expected excess return, and component-model probabilities. Historical snapshots are immutable.

## Display policy

The website may hide low-confidence items from the main surface while preserving them for scoring/diagnostics. Display threshold and portfolio thresholds are defined in `config.json`.

## Paper portfolio relationship

The portfolio normally uses prior-close 5D forecasts and acts at the fixed 09:35 ET window. Portfolio return is not used as the sole measure of model quality.

## Scoring

Primary evaluation includes:

- Brier score;
- log loss;
- calibration;
- Spearman rank IC between expected excess-return ranking and realized excess return;
- component-model Brier scores;
- paper portfolio return after modeled costs;
- SPY benchmark return over the identical live interval.

## Known limitations

- V1 uses a research-grade free market-data adapter rather than a licensed production-grade feed.
- V1 propagation is empirical lead/lag association, not a causal supply-chain or information graph.
- The initial universe is intentionally limited and liquid rather than broad-market exhaustive.
- Many same-day ticker predictions are statistically dependent because they share market conditions.
- V1 does not autonomously add model families or rewrite architecture.

## Versioning rule

Any material change to target definition, feature semantics, model family, data information set, portfolio execution assumption, or learning policy must be recorded. New architecture should normally enter as a challenger/new version rather than silently replacing V1.

<!-- AUTO-SNAPSHOT:START -->
## Automated current snapshot

_Generated from `config.json`, `data/system.json`, and immutable files under `forecasts/`. Do not hand-edit this block._

- **System status:** `live`; phase `live-forward-experiment`; live since: 2026-11-02T20:11:56.438996-05:00.
- **Last successful cycle:** 2026-11-11T19:58:01.271534-05:00; **last recorded error:** none.
- **Forward record:** 8 immutable close snapshots; 960 official forecast observations; 400 resolved live observations.
- **V2 development checkpoint:** not yet reached (8/20 immutable close snapshots).
- **Adaptive ensemble status:** eligible (400/100 resolved live predictions).
- **Official schedule (America/New_York):** premarket 08:45; paper execution 09:35; normal close 16:35; early close 13:35.
- **Forecast target:** relative to `SPY` at 1, 5, 20 trading-session horizons; website display minimum 55.0%.
- **Portfolio gates:** entry probability ≥ 60.0%; exit probability ≤ 52.0%; expected excess-return entry floor 0.4%.
- **Portfolio:** starting cash $1,000; max 4 positions; max position weight 22.5%; cost/slippage 0.1% per side; overnight new-entry veto 4.0% absolute gap.
- **Learning:** rolling 3-year training window; initial weights `broad_logit` 45.0%, `boosted` 35.0%, `momentum_logit` 20.0%; adaptive lookback up to 250 resolved live predictions; weight floor 10.0%; cap 70.0%.
- **Coverage:** 40 forecast-universe equities plus 10 market/context symbols.
- **Data adapter:** `yfinance-research-prototype`; fail closed: `True`.
<!-- AUTO-SNAPSHOT:END -->
