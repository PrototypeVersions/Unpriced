# UNPRICED Methodological Changelog

This changelog records changes that matter to the interpretation of the prospective experiment. Routine daily forecast/data commits do not belong here.

## 2026-11-01 — V1 prospective framework established

- Defined UNPRICED as a forward-only probabilistic market experiment.
- Set official relative-return targets versus SPY at 1, 5, and 20 trading sessions.
- Established V1 model families: broad logistic, gradient boosted, and momentum logistic, with a separate expected-excess-return layer.
- Set initial ensemble weights to 45% / 35% / 20%.
- Set rolling model retraining to three years of historical data.
- Prohibited live ensemble reweighting until at least 100 genuinely live resolved predictions.
- Established immutable dated forecast snapshots and a strict separation between LIVE and historical/research evidence.
- Established fail-closed behavior when required market data are unavailable or stale.

## 2026-11-01 — Daily operating protocol established

- Premarket refresh: 08:45 ET.
- Paper execution: 09:35 ET using the completed 09:30–09:35 five-minute bar.
- Official close cycle: 16:35 ET on normal sessions.
- Official early-close cycle: 13:35 ET.
- Limited the V1 portfolio to one formal execution window per trading day while allowing multiple transactions within that window.

## 2026-11-01 — $1,000 paper portfolio established

- Starting cash: $1,000.
- Long-only; no leverage; no options; fractional shares allowed.
- Maximum four positions and 22.5% target weight per position.
- 10 bps modeled cost/slippage per side.
- New entries use prior-close 5D forecasts and require the configured probability and expected-excess-return thresholds.
- Large overnight gaps can veto new entries under the precommitted rule.
- Portfolio performance is explicitly separated from forecast probability quality.

## 2026-11-01 — V2 challenger plan established

- Preserve V1 without performance-driven redesign for roughly the first 20 trading days, except for genuine bug/data fixes.
- Begin V2 development around the ~20-trading-day checkpoint.
- Run V2 prospectively in shadow/challenger mode before promotion.
- Plan the first serious V1–V2 comparison around ~60 trading days of V1 history, subject to sufficient challenger observations.
- Consider promotion roughly in the 60–90 trading-day region only if multi-dimensional prospective evidence supports it.
- Candidate V2 directions include better point-in-time data, analyst revisions, event semantics, economic relationship graphs, and richer propagation modeling.

## 2026-11-01 — Long-term handoff/documentation system established

- Added `AI_HANDOFF.md`, `DECISIONS.md`, `ROADMAP.md`, `MODEL_CARD_V1.md`, and this changelog.
- Added machine-generated current-state blocks sourced from the repository's canonical configuration/live state.
- Added automated GitHub documentation synchronization so current schedules, thresholds, weights, provider status, forecast counts, and roadmap checkpoints do not rely on a future developer remembering to update prose manually.

## 2026-11-03 — Scheduler reliability and forward-integrity repairs

- Confirmed that GitHub schedules were enabled but could start several hours late.
- Added redundant cron attempts and current-session close recovery on a workflow-code
  repair push; retained the NYSE time-bound information rules and immutable snapshots.
- Forbid retroactive premarket eligibility and late portfolio fills; guard against
  duplicate executions and unfinished five-minute bars.
- Reject stale current-session daily data/features rather than publishing a
  current-dated forecast from a prior day's observation.
- Recorded the hours-late, zero-trade November 3 execution in an additive audit and
  reset only its mutable benchmark start to await a valid morning execution.
- Restored a November 3 post-close snapshot at its actual evening publication time.
- Added periodic in-browser data refresh, generated-docs synchronization during the
  cycle, and schedule-failure regression tests.
- No historical forecast or trade was overwritten, and no V1 model/threshold/
  ensemble architecture was changed.

## Rules for future entries

Add an entry whenever a change materially alters:

- the information set or data source;
- forecast target or horizon;
- feature semantics;
- model family/architecture;
- training or adaptive-learning policy;
- ensemble weights/rules;
- paper-trading rules or execution assumptions;
- scoring/evaluation methodology;
- champion/challenger promotion policy;
- interpretation of the LIVE record.

Do not delete old entries when a decision is superseded. Append the new decision and identify what it supersedes.
