# UNPRICED Design Decisions

This file records major methodological choices and the reasoning behind them. It is intentionally human/AI-authored rather than generated from code.

## D-001 — Prospective evidence is primary

UNPRICED is a forward-only experiment. Historical research may train or diagnose models, but the public test is whether forecasts frozen before outcomes retain skill prospectively.

**Consequence:** backtests cannot be relabeled as LIVE performance, and missed cycles are not backfilled.

## D-002 — Relative returns versus SPY

The main targets are 1D, 5D, and 20D stock returns relative to SPY rather than raw price direction.

**Reason:** this asks whether the system identifies cross-sectional repricing rather than simply benefiting from a rising or falling market.

## D-003 — One formal forecast cycle per trading day

Official probabilities are frozen after the close. Intraday model reactions are not allowed to rewrite them.

**Reason:** one well-defined information boundary makes the experiment auditable and reduces noise, turnover, and dependence on fragile intraday data.

## D-004 — One portfolio execution window per trading day

The V1 portfolio acts at 09:35 ET using prior-close 5D forecasts and precommitted premarket vetoes. A cycle can include multiple transactions, but there is no discretionary intraday re-trading.

**Reason:** this isolates whether UNPRICED's forecast layer adds value rather than turning V1 into an intraday trading system.

## D-005 — Completed first five-minute bar for simulated fills

Paper execution uses the typical price of the completed 09:30–09:35 ET bar rather than an idealized exact opening print.

**Reason:** the system should not claim a fill at information it could not reliably observe and act on in real time.

## D-006 — Fail closed on data problems

Missing or stale required data suppresses the forecast/trade rather than being silently filled or fabricated.

**Reason:** a missing observation is scientifically preferable to invented evidence.

## D-007 — Three deliberately different V1 model families

V1 combines a broad logistic model, a nonlinear boosted model, and a narrow relative-momentum logistic specialist.

**Reason:** disagreement among structurally different models is informative, and a simple specialist provides a useful benchmark against added complexity.

## D-008 — Parameters may learn; architecture may not self-modify

Model parameters retrain automatically on a rolling historical window. Ensemble weights may adapt under a precommitted live-performance rule after sufficient live resolutions. Source code/model architecture does not autonomously redesign itself.

**Reason:** adaptation should be auditable and attributable. New architecture belongs in a new challenger/version.

## D-009 — Live ensemble weights stay frozen initially

Initial V1 weights are 45% broad logistic, 35% boosted, 20% momentum logistic. Live-performance weighting is disabled until at least 100 genuinely live resolved predictions exist.

**Reason:** very small live samples are too noisy to justify performance-driven reweighting.

## D-010 — Forecast quality and portfolio economics are separate

Probability calibration, Brier score, log loss, and rank information coefficient are evaluated independently of portfolio return.

**Reason:** a profitable portfolio can result from a few concentrated outcomes even when probabilities are poor, and good probability estimates can temporarily lose money.

## D-011 — V1 must survive ordinary bad outcomes unchanged

A few losing trades, a bad week, brief SPY underperformance, or a short model losing streak are not reasons to retune V1.

**Reason:** discretionary reaction to short-term outcomes would contaminate the prospective test.

## D-012 — V2 begins as a challenger, not a replacement

Around the first ~20 trading days, V2 development may begin while V1 remains the champion. V2 should make prospective shadow forecasts before any promotion decision.

**Reason:** improvements must earn their status on data that were not available when the challenger was designed.

## D-013 — Promotion requires multi-dimensional evidence

A challenger should not be promoted merely because its paper portfolio made more money. Compare Brier score, log loss, calibration, rank IC, robustness by forecast date/regime, component behavior, and trading economics after costs.

**Reason:** the goal is durable predictive quality, not a lucky trading path.

## D-014 — Same-day forecasts are not treated as independent experiments

Evaluation should aggregate and compare performance by forecast date as well as by ticker-level observation.

**Reason:** many stocks on one day share the same market environment, so apparent sample size can overstate independent evidence.

## D-015 — Better data is an infrastructure upgrade, but must still be versioned

Replacing the research-grade free adapter with a licensed point-in-time feed may occur before V2 if needed for reliability. The forecasting logic can remain V1, but the provider change must be recorded and old artifacts left untouched.

**Reason:** experimental integrity does not require knowingly retaining unreliable plumbing.

## D-016 — Strict clock windows for simulated execution (2026-11-03)

A scheduled run arriving hours late may not claim the first five-minute bar as a
prospective simulated execution. Premarket eligibility must be established before
the opening bell. Paper execution is now valid only 09:35–09:45 ET, at most once per
trading session, using only the completed 09:30 first bar and the immediately prior
NYSE session's official forecast.

**Reason:** A backdated fill or a morning benchmark price assigned in the afternoon
would create look-ahead bias even when the GitHub job itself succeeded.

**Historical handling:** The November 3 late run made zero trades, so the immutable
record is retained with an additive operations audit; only the mutable benchmark
initialization was reset for a valid prospective start.

## D-017 — Redundant schedules without backfilling (2026-11-03)

GitHub's scheduler can delay or drop runs. Short, idempotent retries are permitted
for all cycles. Close-cycle recovery can publish a genuinely new current-session
forecast later in the evening only when the current completed NYSE bar exists, with
its **actual** timestamp. A missed premarket or execution window cannot be replayed.

**Reason:** Preserve availability without improving the apparent forward record by
hindsight. A missing cycle remains an explicitly detectable miss.

## Adding future decisions

Add a new numbered entry whenever a change materially affects what information the system sees, what it predicts, how it learns, how it trades, how it is scored, or how a version is promoted. Do not rewrite old decisions to make later choices look inevitable; append superseding decisions instead.
