# UNPRICED

**A forward-only experiment in probabilistic stock forecasting, information propagation, and disciplined paper trading.**

UNPRICED is designed to answer three separate questions without conflating them:

1. Can a model assign useful probabilities to near-term relative stock performance?
2. Can it identify information that has not fully propagated through related assets?
3. Can those forecasts be converted into a sensible paper-trading process after costs and risk controls?

## Operating schedule

All times use `America/New_York` and the NYSE trading calendar.

- **08:45 ET — Premarket refresh.** Overnight state and risk gates update. Published forecasts are not rewritten.
- **09:35 ET — Paper execution.** The $1,000 experiment may rebalance using only the prior close's frozen 5-day forecasts plus precommitted overnight veto rules. Execution uses the completed 09:30–09:35 five-minute bar, not a perfect opening print.
- **16:35 ET — Official post-close cycle.** Mature forecasts resolve, model weights update under fixed rules, the rolling models retrain, new 1D/5D/20D forecasts are frozen, and the site refreshes. The 35-minute buffer reduces the chance that an incomplete free-data daily bar is mistaken for the final session.
- **Early-close sessions — 13:35 ET.** The same post-close logic runs after the exchange's early close. A redundant 16:35 trigger safely no-ops if the early-close snapshot already exists.

The site therefore receives **two intelligence updates per normal trading day** (premarket and post-close), plus a portfolio-state update after the 09:35 simulated execution.

## Forecast philosophy

UNPRICED emphasizes likely, testable outcomes rather than dramatic tails. The default surface ranks predictions with directional probability at or above 55% and keeps probability separate from expected excess return, uncertainty, model agreement, and economic significance.

The official prediction target is relative performance versus SPY over the next **1, 5, and 20 trading sessions** from the publication close. Exact price targets are intentionally not the primary object.

## Model v1

Three independent price/volume model families run automatically:

- **Broad logistic model** — interpretable nonlinear-free baseline using momentum, reversal, volatility, volume, and market-regime features.
- **Gradient-boosted model** — nonlinear interactions over the same point-in-time feature set.
- **Momentum logistic model** — deliberately simple specialist benchmark.

The initial ensemble weights are frozen at 45% / 35% / 20%. After at least 100 genuinely live resolved forecast observations exist, weights may adapt automatically using recent out-of-sample Brier performance under precommitted floors, caps, and lookback rules. The system retrains parameters on a rolling historical window every close, but it **does not rewrite its own architecture or code**.

## $1,000 Live Portfolio

The paper portfolio starts with exactly **$1,000 cash** and no hindsight. V1 is intentionally conservative:

- long-only;
- no leverage;
- no options;
- fractional shares allowed;
- at most four positions;
- at most 22.5% of equity in one position;
- 10 bps assumed slippage/cost per side;
- new entries require a 5-day outperformance probability of at least 60% and positive expected excess return;
- the system is never forced to trade;
- a large overnight gap can veto a new entry before 09:35 execution.

Forecast accuracy and portfolio performance are scored separately. SPY is tracked as a buy-and-hold benchmark from the experiment's first execution date.

## Automation and auditability

Every official close cycle creates an immutable dated forecast snapshot under `forecasts/`. Every trade is appended to the portfolio ledger. Historical forecasts and trades are never edited to improve the record.

GitHub Actions runs the market cycle automatically on weekdays. The Python engine checks the NYSE calendar before doing anything, so holidays and early closes do not create fake sessions. Scheduled jobs fail closed when required market data are unavailable.

## Data-source status

The first autonomous prototype uses `yfinance` as a research-grade adapter so it can run without credentials. This is intentionally treated as a prototype dependency, not a production-grade licensed feed. The engine exposes stale/provider failures instead of fabricating data. A licensed market-data provider can later replace the adapter without changing historical forecasts.

## Interface

- **Market State** — restrained regime diagnostics, not narrative market calls.
- **Forecasts** — ranked probabilities, expected excess returns, ranges, and model agreement.
- **Propagation** — empirical lead/lag relationships and candidate information gaps, clearly distinguished from causation.
- **Models** — model votes, weights, disagreement, and later a competence map.
- **Track Record** — calibration, Brier score, log score, rank information coefficient, and benchmark comparisons.
- **Live Portfolio** — the autonomous $1,000 paper experiment and complete trade history.

## Future AI / developer handoff

Before modifying forecasting logic, model architecture, scoring, trading rules, data sources, or historical records, read:

1. [`docs/AI_HANDOFF.md`](docs/AI_HANDOFF.md) — read first; project invariants and safe change workflow.
2. [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) — scientific definitions and evaluation.
3. [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — operating/failure policy.
4. [`docs/DECISIONS.md`](docs/DECISIONS.md) — architectural decisions and rationale.
5. [`docs/MODEL_CARD_V1.md`](docs/MODEL_CARD_V1.md) — V1 model specification and limitations.
6. [`docs/ROADMAP.md`](docs/ROADMAP.md) — V2 challenger timeline and longer-term possibilities.
7. [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — substantive methodological changes.

The repo also contains `scripts/sync_docs.py` and `.github/workflows/docs-sync.yml`. They automatically refresh machine-owned status blocks in the handoff/model-card/roadmap from canonical configuration and live state. Future substantive methodological changes should still update `DECISIONS.md`, `ROADMAP.md`, and `CHANGELOG.md` intentionally; code should not invent design rationale after the fact.

## Status

The infrastructure is designed to begin prospectively. Until the first valid scheduled post-close cycle completes, the public interface remains clearly labeled **PRE-LIVE** rather than displaying invented forecasts.
