# UNPRICED Methodology

## 1. Scientific target

UNPRICED is a forward experiment. Its headline claim is not that a model can produce visually impressive historical backtests. The test is whether forecasts frozen before outcomes occur retain skill prospectively.

Official forecasts are made after the regular market close and target stock performance relative to SPY over the next 1, 5, and 20 trading sessions.

## 2. Clock and information sets

### 08:45 America/New_York — premarket refresh

The premarket cycle may update operational state and apply precommitted risk gates to proposed paper-portfolio entries. It **cannot rewrite the prior close's official probability forecast**.

### 09:35 America/New_York — paper execution

Paper trades use only decisions available before execution. The simulated fill is derived from the completed 09:30–09:35 ET five-minute bar. This deliberately avoids claiming an ideal 09:30 opening-auction fill that the system did not observe in real time.

### 16:20 America/New_York — official close cycle

The close cycle uses data through the completed trading session. It resolves outcomes whose horizons have closed, updates allowed ensemble weights using only already-resolved live forecasts, retrains model parameters on historical data available at that time, and freezes a new dated forecast snapshot.

NYSE early-close days use the same logic at 13:20 ET.

## 3. No hindsight

Once written to `forecasts/YYYY-MM-DD-close.json`, a forecast's proposition, probability, horizon, component-model probabilities, expected excess return, and publication timestamp are immutable.

Corrections to data provenance are additive. They do not silently alter the original prediction.

## 4. Targets

For ticker `i`, forecast date `t`, and horizon `h`:

`excess_return(i,t,h) = return(i,t→t+h) - return(SPY,t→t+h)`

The binary event is:

`outperform(i,t,h) = 1 if excess_return(i,t,h) > 0 else 0`

The displayed directional probability is `p(outperform)` when it exceeds 0.5 and `1-p(outperform)` for an underperformance call.

Exact future prices are not the main prediction object.

## 5. Initial model families

### broad_logit

Logistic regression over standardized point-in-time features including short/medium momentum, one-day reversal, realized volatility, volume surprise, relative strength, and market-regime features.

### boosted

A histogram gradient-boosting classifier over the same information set. It is included to capture nonlinear interactions, not because complexity is presumed superior.

### momentum_logit

A deliberately narrow logistic benchmark using only relative momentum features.

Every forecast stores all three probabilities so the ensemble can later be audited.

## 6. Ensemble learning

Initial weights are frozen in `config.json`.

Before 100 live resolved prediction observations exist, weights do not adapt from the live record.

After that threshold, each model receives an exponentially transformed weight based on recent live Brier performance, subject to a minimum 10% and maximum 70% allocation. Only genuinely resolved forward forecasts enter this update. Historical training/backtest rows never masquerade as live performance.

This is parameter adaptation, not architecture self-modification. New model families require a new version and cannot retroactively participate in earlier forecasts.

## 7. Forecast selection

The website defaults to directional probabilities of at least 55%. A forecast may still exist below the display threshold for scoring and diagnostics, but low-confidence items are not promoted as the product's main surface.

## 8. Paper portfolio

The Live Portfolio is a separate economic experiment. It does not determine whether probabilities were calibrated.

V1 rules:

- initial cash: $1,000;
- long-only;
- fractional shares;
- no leverage or options;
- maximum four holdings;
- maximum 22.5% target weight per holding;
- 10 bps synthetic cost/slippage per side;
- candidate comes from the prior close's 5-day forecasts;
- entry requires `p(outperform SPY) >= 0.60` and expected excess return >= 0.40%;
- exit threshold is `p(outperform SPY) <= 0.52` or portfolio/risk rule;
- no obligation to trade;
- absolute premarket gap >= 4% vetoes a new entry for that session.

The portfolio's simulated execution is not a claim that a broker actually accepted an order.

## 9. Scoring

UNPRICED keeps several records separate:

- **Brier score** for directional probabilities;
- **log loss** for probability quality;
- **calibration bins**;
- **Spearman information coefficient** between expected excess return/ranking and realized excess return;
- **component-model Brier scores**;
- **paper portfolio return after synthetic costs**;
- **SPY benchmark return over the identical live interval**.

Profit is never accepted as a substitute for probability accuracy.

## 10. Market-state layer

The public Market State surface is intentionally restrained. It reports measured state variables such as trend, breadth, dispersion, realized volatility, VIX, rates, and sector relative strength. It does not generate large prose claims merely to sound prescient.

## 11. Propagation layer

V1 may estimate empirical lead/lag relationships from historical returns. These are labeled empirical associations, **not causal links**. A later version may add supplier/customer/industry relationships from licensed or explicitly sourced fundamental data.

## 12. Failure behavior

If required data are missing, stale, internally inconsistent, or unavailable, the engine fails closed:

- no fabricated forecast;
- no fabricated fill;
- no silent forward-fill across an official publication boundary;
- public health state records the failure/staleness.

A missed forecast is preferable to an invented one.
