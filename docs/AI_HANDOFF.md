# UNPRICED — AI / Developer Handoff

> **Read this before changing forecasting logic, scoring, trading rules, data sources, or historical records.**

UNPRICED is a forward-only market-forecasting laboratory. Its value comes from preserving a clean distinction between predictions made before outcomes and analysis performed afterward. A future AI should optimize for experimental integrity before optimizing for apparent performance.

## Purpose

UNPRICED asks whether structured models can detect information or consequences that have not yet fully propagated into relative stock prices. The public website presents Market State, ranked Forecasts, empirical Propagation gaps, component Models, a prospective Track Record, and a separate $1,000 paper portfolio.

The primary forecast target is relative performance versus SPY over 1, 5, and 20 trading sessions. Exact price targets are intentionally secondary.

## Read these files next

1. `docs/METHODOLOGY.md` — scientific definitions and scoring.
2. `docs/OPERATIONS.md` — daily operation and failure policy.
3. `docs/DECISIONS.md` — why important architectural choices were made.
4. `docs/MODEL_CARD_V1.md` — frozen V1 model/trading specification.
5. `docs/ROADMAP.md` — challenger/version plan.
6. `docs/CHANGELOG.md` — substantive methodological changes.
7. `config.json` — machine-readable current configuration.

## Invariants — do not break without explicit versioning

- **Never edit or replace an official historical live forecast.** Corrections are additive.
- **Never backfill a missed forecast and label it live.** A missed cycle remains missed.
- **Never mix historical/backtest rows with the prospective LIVE record.**
- **Never let later outcomes influence an earlier forecast, fill, probability, or timestamp.**
- **Never silently change a model family, feature definition, target, threshold, data source, execution assumption, or scoring rule.** Material changes require a dated changelog entry and normally a new model/version.
- **Never promote a challenger based only on portfolio profit.** Probability quality, calibration, ranking skill, robustness across dates/regimes, and trading economics must be examined separately.
- **Never tune V1 because of a few losses, a bad week, or temporary SPY underperformance.** Fix genuine software/data bugs; do not hindsight-optimize ordinary outcomes.
- **Forecast skill and paper-portfolio performance remain separate experiments.**
- **Fail closed.** If required data are unavailable or stale, do not fabricate a forecast or fill.
- **Architecture does not self-modify.** Parameter retraining and precommitted ensemble reweighting are allowed; new architecture enters as an explicit challenger/version.

## Daily information boundary

- **08:45 ET — premarket refresh:** operational state and precommitted vetoes may update; prior-close probabilities may not be rewritten.
- **09:35 ET — paper execution:** acts on prior-close frozen 5D forecasts plus precommitted premarket gates. Fill uses the completed 09:30–09:35 five-minute bar.
- **16:35 ET — official post-close cycle:** resolve matured outcomes, update allowed live-based weights, retrain rolling model parameters, freeze new 1D/5D/20D predictions, update Market State/Propagation, and write an immutable snapshot.
- **13:35 ET on NYSE early-close days.**

NYSE calendar logic controls holidays and early closes. GitHub scheduling can be late; preserve the actual run/publication timestamp.

## V1 architecture

V1 contains three directional model families plus an expected-excess-return model:

- `broad_logit` — broad interpretable logistic model;
- `boosted` — histogram gradient-boosted classifier;
- `momentum_logit` — deliberately narrow relative-momentum specialist;
- Ridge-style expected excess-return regression used for ranking/economic filtering.

Model parameters retrain on a rolling three-year historical window after valid closes. Initial ensemble weights are 45% / 35% / 20%. Live ensemble adaptation begins only after the configured minimum number of genuinely live resolved predictions and uses recent live Brier performance with fixed floors/caps/lookback rules.

V1 Propagation is empirical lead/lag association, not a causal network. V1 Market State summarizes measured trend, breadth, dispersion, volatility, VIX, rates, and sector-relative conditions.

## $1,000 paper experiment

The portfolio starts with exactly $1,000 cash and can remain in cash. It is long-only, unlevered, uses fractional shares, holds at most four positions, applies position caps and synthetic costs, and normally acts once per day at the 09:35 execution window. A single execution cycle may contain multiple buys/sells; it is not limited to one transaction.

The portfolio is an economic translation of forecasts, not the definition of forecast success.

## V2 / challenger principle

V1 should accumulate a prospective record without performance-driven redesign during roughly the first 20 trading days, apart from genuine bug/data fixes. Around that checkpoint, development of a V2 challenger may begin. V2 should issue its own frozen shadow forecasts without controlling the official V1 portfolio.

A first serious V1–V2 comparison is planned around ~60 trading days of V1 history, with promotion considered roughly in the 60–90 trading-day region only if prospective evidence supports it. Compare by forecast date as well as by individual ticker observation because same-day stock forecasts are correlated.

Likely V2 directions include better point-in-time/licensed data, analyst estimate revisions, earnings/filing semantic changes, supplier/customer/competitor networks, richer propagation structure, and later options-market information. See `docs/ROADMAP.md`.

## Documentation automation

`python scripts/sync_docs.py` regenerates machine-owned status blocks in this file, `docs/MODEL_CARD_V1.md`, and `docs/ROADMAP.md` from `config.json`, `data/system.json`, and the immutable forecast directory. `.github/workflows/docs-sync.yml` runs this after relevant state/config changes and on a weekly safety schedule.

**Do not hand-edit text between `AUTO-SNAPSHOT` markers.** Everything outside those markers is deliberate design rationale and should only be changed intentionally. When a substantive methodology change is made, update `docs/DECISIONS.md`, `docs/ROADMAP.md` if relevant, and `docs/CHANGELOG.md` in the same change.

<!-- AUTO-SNAPSHOT:START -->
## Automated current snapshot

_Generated from `config.json`, `data/system.json`, and immutable files under `forecasts/`. Do not hand-edit this block._

- **System status:** `live`; phase `live-forward-experiment`; live since: 2026-11-02T20:11:56.438996-05:00.
- **Last successful cycle:** 2026-11-05T18:49:10.394293-05:00; **last recorded error:** none.
- **Forward record:** 4 immutable close snapshots; 480 official forecast observations; 120 resolved live observations.
- **V2 development checkpoint:** not yet reached (4/20 immutable close snapshots).
- **Adaptive ensemble status:** eligible (120/100 resolved live predictions).
- **Official schedule (America/New_York):** premarket 08:45; paper execution 09:35; normal close 16:35; early close 13:35.
- **Forecast target:** relative to `SPY` at 1, 5, 20 trading-session horizons; website display minimum 55.0%.
- **Portfolio gates:** entry probability ≥ 60.0%; exit probability ≤ 52.0%; expected excess-return entry floor 0.4%.
- **Portfolio:** starting cash $1,000; max 4 positions; max position weight 22.5%; cost/slippage 0.1% per side; overnight new-entry veto 4.0% absolute gap.
- **Learning:** rolling 3-year training window; initial weights `broad_logit` 45.0%, `boosted` 35.0%, `momentum_logit` 20.0%; adaptive lookback up to 250 resolved live predictions; weight floor 10.0%; cap 70.0%.
- **Coverage:** 40 forecast-universe equities plus 10 market/context symbols.
- **Data adapter:** `yfinance-research-prototype`; fail closed: `True`.
<!-- AUTO-SNAPSHOT:END -->
## Safe workflow for future changes

1. Read the files above and inspect the current LIVE record before editing.
2. Decide whether the change is a bug fix, infrastructure change, parameter-policy change, or new model/version.
3. Preserve all prior forecast/trade artifacts.
4. Add tests or validation for the change.
5. Update Decisions/Roadmap/Changelog when the change is substantive.
6. Run `python scripts/sync_docs.py`.
7. Keep V1 and any challenger outputs separately attributable.
8. Never claim a new method's performance on forecasts created before that method existed.
