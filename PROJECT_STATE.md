# UNPRICED — Persistent Project State

## Identity
- Repository: `PrototypeVersions/Unpriced`
- Public name: **UNPRICED**
- Purpose: live forward-only experiment in probabilistic stock forecasting, information propagation, and disciplined paper trading.
- Default market: liquid U.S. equities.
- Benchmark: SPY.
- Public product posture: restrained/high-tech; numbers first; no oversized predictive claims.

## Operating schedule
All times are `America/New_York` and market-calendar gated.

- **08:45 ET:** premarket operational/risk refresh. Does not rewrite published probabilities.
- **09:35 ET:** paper portfolio execution using the completed 09:30–09:35 five-minute bar.
- **16:35 ET:** official close-cycle forecast publication after a 35-minute data-settlement buffer.
- **13:35 ET:** early-close fallback. A later 16:35 trigger no-ops if a snapshot already exists.

## Forecast targets
Official close-cycle predictions target relative performance versus SPY over:
- 1 trading day;
- 5 trading days;
- 20 trading days.

Default UI promotes directional probability >=55%.
Exact future price targets are not the primary prediction object.

## Model v1
- `broad_logit` — standardized full feature logistic regression.
- `boosted` — histogram gradient boosting over the same point-in-time features.
- `momentum_logit` — deliberately narrow relative-momentum benchmark.
- expected excess return estimated separately by ridge regression.

Initial ensemble weights: 45% / 35% / 20%.

### Learning
- model parameters retrain automatically after every valid close on a rolling three-year window;
- initial ensemble weights remain frozen until 100 genuinely live resolved prediction observations exist;
- after the threshold, weights adapt from recent live Brier performance under precommitted 10% floors, 70% caps, and a 250-observation lookback;
- architecture self-modification is forbidden;
- future model families must be versioned challengers and cannot receive retroactive credit.

## Market state
Measured state only: SPY trend, breadth, cross-sectional dispersion, realized volatility, VIX when available, 10Y yield when available, and sector relative strength.

No narrative market headline is required.

## Propagation v1
Empirical one-session lead/lag return relationships among the liquid-stock universe. These are associations, not causal claims. Candidate gaps require a large standardized leader move and a relatively muted lagger move.

Future versions may add supplier/customer/industry graphs from licensed or explicitly sourced fundamental data.

## $1,000 Live Portfolio
Starts prospectively with $1,000 cash.

V1:
- long-only;
- fractional shares;
- no leverage;
- no options;
- max 4 positions;
- max 22.5% position weight;
- 10 bp synthetic cost/slippage per side;
- entry: 5D `p(outperform SPY) >= 0.60`, expected excess return >=0.40%, at least 2/3 models bullish;
- exit: 5D `p(outperform SPY) <= 0.52`;
- absolute premarket gap >=4% vetoes a new entry;
- missing premarket eligibility also vetoes entry;
- system is never forced to trade.

Portfolio performance is separate from forecast accuracy. SPY buy-and-hold is the live benchmark.

## Immutable record
- dated official forecasts: `forecasts/YYYY-MM-DD-close.json`;
- cycle snapshots: `states/`;
- current pointers/state: `data/`;
- methodology: `docs/METHODOLOGY.md`.

Never edit an old official forecast to improve its score.

## Scoring
Track separately:
- Brier score;
- log loss;
- calibration bins;
- Spearman rank information coefficient;
- component-model Brier score;
- paper portfolio return after synthetic costs;
- SPY benchmark return.

## Automation
`.github/workflows/market-cycle.yml` runs the autonomous weekday cycle and commits generated state with the GitHub Actions token.

Important GitHub behavior: state commits made by the workflow token are not relied upon to trigger a second workflow. The market-cycle workflow attempts its own Pages deployment after the forward-record commit.

The market-data adapter is currently `yfinance` so the prototype can run without credentials. It is explicitly research-grade. Missing/stale required data cause a fail-closed run, not a fabricated forecast or fill.

## Pages status
GitHub Pages deployment workflow exists, but the repository-level Pages feature may require a one-time owner setting because the workflow token cannot create a Pages site when the integration lacks that administration permission.

Once Pages is enabled with **GitHub Actions** as the source, both push deployments and scheduled-cycle deployments are already configured.

Expected URL after enablement: `https://prototypeversions.github.io/Unpriced/`

## Next priorities after first live close cycle
1. Verify first live forecast snapshot and first Tuesday paper execution.
2. Add a licensed market-data adapter if reliability warrants it.
3. Add a richer fundamental/news/options propagation layer as separate model families, without rewriting v1 history.
4. Add champion/challenger architecture only after enough live observations exist to evaluate it honestly.
5. Build competence-map diagnostics by horizon/regime once the forward sample is large enough.
