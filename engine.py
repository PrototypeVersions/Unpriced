from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FORECASTS = ROOT / "forecasts"
STATES = ROOT / "states"
TZ = ZoneInfo("America/New_York")

CONFIG = json.loads((ROOT / "config.json").read_text())
UNIVERSE = CONFIG["universe"]
CONTEXT = CONFIG["contextSymbols"]
BENCHMARK = CONFIG["forecast"]["benchmark"]
ALL_SYMBOLS = list(dict.fromkeys(UNIVERSE + CONTEXT))
HORIZONS = CONFIG["forecast"]["horizons"]


def now_et() -> datetime:
    return datetime.now(TZ)


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n")


def iso(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, pd.Timestamp):
        dt = dt.to_pydatetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ).isoformat()


def nyse_session(date_str: str):
    cal = mcal.get_calendar("NYSE")
    sched = cal.schedule(start_date=date_str, end_date=date_str)
    if sched.empty:
        return None
    row = sched.iloc[0]
    return {
        "open": row["market_open"].tz_convert(TZ).to_pydatetime(),
        "close": row["market_close"].tz_convert(TZ).to_pydatetime(),
    }


def download_daily(period: str = "5y") -> dict[str, pd.DataFrame]:
    raw = yf.download(
        ALL_SYMBOLS,
        period=period,
        interval="1d",
        auto_adjust=True,
        actions=False,
        group_by="ticker",
        threads=False,
        progress=False,
    )
    if raw.empty:
        raise RuntimeError("daily market-data download returned no rows")
    out = {}
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = set(raw.columns.get_level_values(0))
        for symbol in ALL_SYMBOLS:
            if symbol not in level0:
                continue
            df = raw[symbol].copy().dropna(how="all")
            if not df.empty:
                out[symbol] = df
    else:
        out[ALL_SYMBOLS[0]] = raw.copy().dropna(how="all")
    if BENCHMARK not in out:
        raise RuntimeError("SPY data unavailable")
    available = [s for s in UNIVERSE if s in out and len(out[s]) >= 100]
    if len(available) < max(10, len(UNIVERSE) // 2):
        raise RuntimeError(f"insufficient universe coverage: {len(available)} symbols")
    return out


def align_panel(frames: dict[str, pd.DataFrame], symbols: list[str]):
    closes, volumes = {}, {}
    for symbol in symbols:
        if symbol not in frames:
            continue
        df = frames[symbol]
        if "Close" in df:
            closes[symbol] = df["Close"].astype(float)
        if "Volume" in df:
            volumes[symbol] = df["Volume"].astype(float)
    close = pd.DataFrame(closes).sort_index()
    volume = pd.DataFrame(volumes).reindex(close.index)
    return close, volume


FEATURES = [
    "ret1", "mom5", "mom20", "mom60", "rel5", "rel20", "rel60",
    "vol20", "vol_ratio", "volume_z20", "spy_mom20", "spy_vol20",
    "breadth20", "dispersion20",
]


def make_feature_panel(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    if BENCHMARK not in close:
        raise RuntimeError("SPY close series unavailable")
    returns = close.pct_change()
    spy = close[BENCHMARK]
    spy_ret = spy.pct_change()
    universe_cols = [s for s in UNIVERSE if s in close.columns]
    ma20 = close[universe_cols].rolling(20).mean()
    breadth20 = (close[universe_cols] > ma20).mean(axis=1)
    dispersion20 = returns[universe_cols].rolling(20).std().mean(axis=1)
    spy_mom20 = spy.pct_change(20)
    spy_vol20 = spy_ret.rolling(20).std() * np.sqrt(252)
    rows = []
    for symbol in universe_cols:
        px = close[symbol]
        r = px.pct_change()
        vol = volume[symbol].replace(0, np.nan) if symbol in volume else pd.Series(index=px.index, dtype=float)
        logv = np.log(vol)
        vz = (logv - logv.rolling(20).mean()) / logv.rolling(20).std().replace(0, np.nan)
        df = pd.DataFrame(index=close.index)
        df["ticker"] = symbol
        df["ret1"] = r
        df["mom5"] = px.pct_change(5)
        df["mom20"] = px.pct_change(20)
        df["mom60"] = px.pct_change(60)
        df["rel5"] = df["mom5"] - spy.pct_change(5)
        df["rel20"] = df["mom20"] - spy.pct_change(20)
        df["rel60"] = df["mom60"] - spy.pct_change(60)
        df["vol20"] = r.rolling(20).std() * np.sqrt(252)
        df["vol_ratio"] = df["vol20"] / spy_vol20.replace(0, np.nan)
        df["volume_z20"] = vz
        df["spy_mom20"] = spy_mom20
        df["spy_vol20"] = spy_vol20
        df["breadth20"] = breadth20
        df["dispersion20"] = dispersion20
        df["date"] = df.index
        rows.append(df.reset_index(drop=True))
    panel = pd.concat(rows, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])
    return panel


def attach_targets(panel: pd.DataFrame, close: pd.DataFrame, horizon: int) -> pd.DataFrame:
    spy_fwd = close[BENCHMARK].shift(-horizon) / close[BENCHMARK] - 1.0
    parts = []
    for symbol in sorted(panel["ticker"].unique()):
        if symbol not in close:
            continue
        d = panel[panel["ticker"] == symbol].copy().set_index("date")
        fwd = close[symbol].shift(-horizon) / close[symbol] - 1.0
        d["fwd_return"] = fwd.reindex(d.index)
        d["spy_fwd_return"] = spy_fwd.reindex(d.index)
        d["excess_return"] = d["fwd_return"] - d["spy_fwd_return"]
        d["target"] = np.where(d["excess_return"].notna(), (d["excess_return"] > 0).astype(float), np.nan)
        parts.append(d.reset_index())
    return pd.concat(parts, ignore_index=True)


@dataclass
class HorizonModels:
    broad: Pipeline
    boosted: HistGradientBoostingClassifier
    momentum: Pipeline
    regressor: Pipeline


def fit_models(training: pd.DataFrame) -> HorizonModels:
    train = training.dropna(subset=FEATURES + ["target", "excess_return"]).copy()
    if len(train) < 1000:
        raise RuntimeError(f"insufficient training rows: {len(train)}")
    X = train[FEATURES].astype(float)
    y = train["target"].astype(int)
    yreg = train["excess_return"].astype(float)
    broad = Pipeline([
        ("scale", StandardScaler()),
        ("model", LogisticRegression(max_iter=400, C=0.7, class_weight="balanced")),
    ])
    broad.fit(X, y)
    boosted = HistGradientBoostingClassifier(
        max_iter=160,
        learning_rate=0.05,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        min_samples_leaf=40,
        random_state=20261102,
    )
    boosted.fit(X, y)
    momentum = Pipeline([
        ("scale", StandardScaler()),
        ("model", LogisticRegression(max_iter=300, C=0.5, class_weight="balanced")),
    ])
    momentum.fit(train[["rel5", "rel20", "rel60"]].astype(float), y)
    regressor = Pipeline([
        ("scale", StandardScaler()),
        ("model", Ridge(alpha=12.0)),
    ])
    regressor.fit(X, yreg)
    return HorizonModels(broad=broad, boosted=boosted, momentum=momentum, regressor=regressor)


def predict_current(models: HorizonModels, current: pd.DataFrame, weights: dict[str, float]) -> list[dict]:
    rows = current.dropna(subset=FEATURES).copy()
    if rows.empty:
        return []
    X = rows[FEATURES].astype(float)
    p_broad = models.broad.predict_proba(X)[:, 1]
    p_boost = models.boosted.predict_proba(X)[:, 1]
    p_mom = models.momentum.predict_proba(rows[["rel5", "rel20", "rel60"]].astype(float))[:, 1]
    expected = models.regressor.predict(X)
    out = []
    for i, (_, row) in enumerate(rows.iterrows()):
        probs = {
            "broad_logit": float(p_broad[i]),
            "boosted": float(p_boost[i]),
            "momentum_logit": float(p_mom[i]),
        }
        p = sum(weights[k] * probs[k] for k in weights)
        out.append({
            "ticker": row["ticker"],
            "pOutperform": round(float(p), 6),
            "direction": "outperform" if p >= 0.5 else "underperform",
            "directionProbability": round(float(max(p, 1 - p)), 6),
            "expectedExcessReturn": round(float(expected[i]), 6),
            "modelProbabilities": {k: round(v, 6) for k, v in probs.items()},
            "modelVotesOutperform": int(sum(v > 0.5 for v in probs.values())),
        })
    return out


def compute_market_state(close: pd.DataFrame, session_date: str) -> dict:
    universe = [s for s in UNIVERSE if s in close.columns]
    spy = close[BENCHMARK].dropna()
    returns = close[universe].pct_change()
    breadth = float((close[universe].iloc[-1] > close[universe].rolling(20).mean().iloc[-1]).mean())
    dispersion = float(returns.tail(20).std().mean())
    spy5 = float(spy.pct_change(5).iloc[-1])
    spy20 = float(spy.pct_change(20).iloc[-1])
    spy_vol = float(spy.pct_change().tail(20).std() * np.sqrt(252))
    vix = float(close["^VIX"].dropna().iloc[-1]) if "^VIX" in close and not close["^VIX"].dropna().empty else None
    tnx = float(close["^TNX"].dropna().iloc[-1]) if "^TNX" in close and not close["^TNX"].dropna().empty else None
    rate20 = None
    if "^TNX" in close and len(close["^TNX"].dropna()) > 20:
        t = close["^TNX"].dropna()
        rate20 = float(t.iloc[-1] - t.iloc[-21])
    if spy20 > 0.02 and (vix is None or vix < 22):
        regime = "risk-on"
    elif spy20 < -0.02 and (vix is None or vix > 22):
        regime = "risk-off"
    else:
        regime = "mixed"
    sector = {}
    for sym in ["QQQ", "SMH", "XLF", "XLE", "XLV", "XLI", "XLU"]:
        if sym in close and len(close[sym].dropna()) > 20:
            c = close[[sym, BENCHMARK]].dropna()
            if len(c) > 20:
                sector[sym] = round(float(c[sym].pct_change(20).iloc[-1] - c[BENCHMARK].pct_change(20).iloc[-1]), 6)
    return {
        "status": "live",
        "asOf": iso(now_et()),
        "sessionDate": session_date,
        "regime": regime,
        "metrics": {
            "spy5dReturn": round(spy5, 6),
            "spy20dReturn": round(spy20, 6),
            "breadthAbove20dMA": round(breadth, 6),
            "crossSectionDispersion20d": round(dispersion, 6),
            "spyRealizedVol20d": round(spy_vol, 6),
            "vix": None if vix is None else round(vix, 4),
            "tenYearYield": None if tnx is None else round(tnx, 4),
            "tenYear20dChange": None if rate20 is None else round(rate20, 4),
            "sectorRelative20d": sector,
        },
        "interpretation": {
            "breadth": "broad" if breadth >= 0.65 else "narrow" if breadth <= 0.40 else "mixed",
            "dispersion": "high" if dispersion >= 0.035 else "low" if dispersion <= 0.018 else "moderate",
            "volatility": "high" if spy_vol >= 0.28 else "low" if spy_vol <= 0.14 else "moderate",
        },
    }


def compute_propagation(close: pd.DataFrame, session_date: str) -> dict:
    symbols = [s for s in UNIVERSE if s in close.columns]
    ret = close[symbols].pct_change().dropna(how="all")
    if len(ret) < 90:
        return {"status": "insufficient-history", "asOf": iso(now_et()), "method": "empirical-lead-lag-v1", "edges": [], "gaps": []}
    recent = ret.tail(180)
    edges = []
    for lead in symbols:
        shifted = recent[lead].shift(1)
        for lag in symbols:
            if lead == lag:
                continue
            pair = pd.concat([shifted, recent[lag]], axis=1).dropna()
            if len(pair) < 80:
                continue
            corr = pair.iloc[:, 0].corr(pair.iloc[:, 1])
            if pd.notna(corr) and corr > 0.18:
                edges.append((float(corr), lead, lag))
    edges.sort(reverse=True)
    kept = [{"from": a, "to": b, "lag1Correlation": round(c, 4)} for c, a, b in edges[:24]]
    today = ret.iloc[-1]
    z = (today - ret.tail(60).mean()) / ret.tail(60).std().replace(0, np.nan)
    gaps = []
    for edge in kept:
        lead, lag = edge["from"], edge["to"]
        if pd.isna(z.get(lead)) or pd.isna(z.get(lag)):
            continue
        if abs(z[lead]) >= 1.5 and abs(z[lag]) <= 0.6:
            gaps.append({
                "leader": lead,
                "lagger": lag,
                "leaderMoveZ": round(float(z[lead]), 3),
                "laggerMoveZ": round(float(z[lag]), 3),
                "lag1Correlation": edge["lag1Correlation"],
                "direction": "positive-follow-through" if z[lead] > 0 else "negative-follow-through",
            })
    gaps.sort(key=lambda g: abs(g["leaderMoveZ"]) * g["lag1Correlation"], reverse=True)
    return {
        "status": "live",
        "asOf": iso(now_et()),
        "sessionDate": session_date,
        "method": "empirical-lead-lag-v1",
        "edges": kept,
        "gaps": gaps[:10],
        "note": "Empirical lagged return associations only; not causal relationships.",
    }


def forecast_snapshots() -> list[Path]:
    return sorted(FORECASTS.glob("*-close.json"))


def resolve_forecasts(close: pd.DataFrame) -> dict:
    track = read_json(DATA / "track-record.json")
    existing = {(r["snapshotId"], r["ticker"], int(r["horizon"])) for r in track.get("resolved", [])}
    spy = close[BENCHMARK].dropna()
    dates = list(spy.index)
    for path in forecast_snapshots():
        snap = read_json(path)
        candidates = [d for d in dates if pd.Timestamp(d).date().isoformat() == snap["sessionDate"]]
        if not candidates:
            continue
        start = candidates[-1]
        start_pos = dates.index(start)
        for f in snap.get("forecasts", []):
            key = (snap["snapshotId"], f["ticker"], int(f["horizon"]))
            if key in existing:
                continue
            h = int(f["horizon"])
            end_pos = start_pos + h
            if end_pos >= len(dates):
                continue
            end = dates[end_pos]
            ticker = f["ticker"]
            if ticker not in close or start not in close[ticker].index or end not in close[ticker].index:
                continue
            if pd.isna(close[ticker].loc[start]) or pd.isna(close[ticker].loc[end]):
                continue
            asset_ret = float(close[ticker].loc[end] / close[ticker].loc[start] - 1)
            spy_ret = float(spy.loc[end] / spy.loc[start] - 1)
            excess = asset_ret - spy_ret
            outcome = 1 if excess > 0 else 0
            p = float(f["pOutperform"])
            brier = (p - outcome) ** 2
            eps = 1e-9
            log_loss = -(outcome * math.log(max(p, eps)) + (1 - outcome) * math.log(max(1 - p, eps)))
            track["resolved"].append({
                "snapshotId": snap["snapshotId"], "publishedAt": snap["publishedAt"], "sessionDate": snap["sessionDate"],
                "ticker": ticker, "horizon": h, "pOutperform": p, "expectedExcessReturn": f["expectedExcessReturn"],
                "modelProbabilities": f["modelProbabilities"], "outcome": outcome,
                "assetReturn": round(asset_ret, 8), "spyReturn": round(spy_ret, 8),
                "realizedExcessReturn": round(excess, 8), "resolvedAt": pd.Timestamp(end).date().isoformat(),
                "brier": round(brier, 8), "logLoss": round(log_loss, 8),
            })
            existing.add(key)
    resolved = track.get("resolved", [])
    if resolved:
        track["status"] = "live"
        track["metrics"]["resolvedCount"] = len(resolved)
        track["metrics"]["brier"] = round(float(np.mean([r["brier"] for r in resolved])), 8)
        track["metrics"]["logLoss"] = round(float(np.mean([r["logLoss"] for r in resolved])), 8)
        df = pd.DataFrame(resolved)
        ics = []
        for _, group in df.groupby(["snapshotId", "horizon"]):
            if len(group) >= 8:
                ic = spearmanr(group["expectedExcessReturn"], group["realizedExcessReturn"]).statistic
                if pd.notna(ic):
                    ics.append(float(ic))
        track["metrics"]["rankIC"] = None if not ics else round(float(np.mean(ics)), 6)
        bins = []
        for lo in np.arange(0.0, 1.0, 0.1):
            hi = lo + 0.1
            members = [r for r in resolved if lo <= r["pOutperform"] < hi or (hi >= 1 and r["pOutperform"] == 1)]
            if members:
                bins.append({
                    "low": round(float(lo), 1), "high": round(float(hi), 1), "n": len(members),
                    "meanForecast": round(float(np.mean([r["pOutperform"] for r in members])), 4),
                    "observedFrequency": round(float(np.mean([r["outcome"] for r in members])), 4),
                })
        track["metrics"]["calibration"] = bins
        model_metrics = {}
        for model in ["broad_logit", "boosted", "momentum_logit"]:
            vals = [(float(r["modelProbabilities"][model]) - r["outcome"]) ** 2 for r in resolved if model in r.get("modelProbabilities", {})]
            model_metrics[model] = {"resolvedCount": len(vals), "brier": None if not vals else round(float(np.mean(vals)), 8)}
        track["modelMetrics"] = model_metrics
    track["updatedAt"] = iso(now_et())
    return track


def adaptive_weights(track: dict):
    resolved = track.get("resolved", [])
    threshold = int(CONFIG["learning"]["adaptiveWeightingStartsAfterResolvedPredictions"])
    initial = CONFIG["learning"]["initialModelWeights"]
    if len(resolved) < threshold:
        return initial, "frozen-initial", len(resolved)
    recent = resolved[-int(CONFIG["learning"]["adaptiveLookbackResolvedPredictions"]):]
    temp = float(CONFIG["learning"]["brierTemperature"])
    floor = float(CONFIG["learning"]["weightFloor"])
    cap = float(CONFIG["learning"]["weightCap"])
    raw = {}
    for model in initial:
        vals = [(float(r["modelProbabilities"][model]) - r["outcome"]) ** 2 for r in recent if model in r.get("modelProbabilities", {})]
        brier = float(np.mean(vals)) if vals else 0.25
        raw[model] = math.exp(-temp * brier)
    total = sum(raw.values())
    weights = {k: v / total for k, v in raw.items()}
    for _ in range(12):
        weights = {k: min(cap, max(floor, v)) for k, v in weights.items()}
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
    return {k: round(v, 8) for k, v in weights.items()}, "adaptive-live-brier", len(resolved)


def build_forecast_snapshot(frames: dict[str, pd.DataFrame], session_date: str, weights: dict[str, float]) -> dict:
    close, volume = align_panel(frames, ALL_SYMBOLS)
    panel = make_feature_panel(close, volume)
    cutoff = pd.Timestamp(session_date)
    min_date = cutoff - pd.DateOffset(years=int(CONFIG["learning"]["rollingTrainingYears"]))
    forecasts, ranges = [], []
    benchmark_dates = sorted(close[BENCHMARK].dropna().index)
    matching = [i for i, d in enumerate(benchmark_dates) if pd.Timestamp(d).date() == cutoff.date()]
    cutoff_pos = matching[-1] if matching else len(benchmark_dates) - 1
    for horizon in HORIZONS:
        targeted = attach_targets(panel, close, horizon)
        safe_dates = set(pd.Timestamp(x) for x in benchmark_dates[:max(0, cutoff_pos - horizon + 1)])
        train = targeted[(targeted["date"] >= min_date) & (targeted["date"] < cutoff) & targeted["date"].isin(safe_dates)].copy()
        models = fit_models(train)
        current = panel[panel["date"].dt.date == cutoff.date()].copy()
        if current.empty:
            raise RuntimeError(f"No current-session features for {session_date}; refusing stale forecast")
        preds = predict_current(models, current, weights)
        for p in preds:
            p["horizon"] = int(horizon)
            forecasts.append(p)
        ranges.append({
            "horizon": int(horizon), "rows": int(len(train)),
            "start": None if train.empty else train["date"].min().date().isoformat(),
            "end": None if train.empty else train["date"].max().date().isoformat(),
        })
    forecasts.sort(key=lambda f: (f["horizon"], -f["directionProbability"], -abs(f["expectedExcessReturn"])))
    return {
        "schemaVersion": 1,
        "snapshotId": f"{session_date}-close-v1",
        "status": "published-live",
        "publishedAt": iso(now_et()),
        "sessionDate": session_date,
        "informationCutoff": f"{session_date} official NYSE close",
        "modelVersion": "v1.0.0",
        "ensembleWeights": weights,
        "trainingRanges": ranges,
        "forecastDefinition": "Relative performance versus SPY from publication close to future close.",
        "forecasts": forecasts,
    }


def mark_portfolio(portfolio: dict, price_map: dict[str, float], at: str) -> dict:
    value = float(portfolio.get("cash", 0))
    for pos in portfolio.get("positions", []):
        price = price_map.get(pos["ticker"])
        if price is not None and price > 0:
            pos["lastPrice"] = round(float(price), 6)
        use = float(pos.get("lastPrice") or pos.get("entryPrice"))
        pos["marketValue"] = round(float(pos["shares"]) * use, 6)
        value += pos["marketValue"]
    portfolio["equity"] = round(value, 6)
    portfolio["lastMarkedAt"] = at
    return portfolio


def update_benchmark(portfolio: dict, spy_price: float | None) -> None:
    b = portfolio["benchmark"]
    if spy_price is None or spy_price <= 0:
        return
    if b.get("startedAt") and b.get("entryPrice"):
        b["currentValue"] = round(float(b["startingValue"]) * float(spy_price) / float(b["entryPrice"]), 6)


def postclose_mode() -> None:
    now = now_et()
    date_str = now.date().isoformat()
    session = nyse_session(date_str)
    if session is None:
        print("No NYSE session today; close cycle no-op.")
        return
    if now < session["close"] + timedelta(minutes=15):
        print("Market not closed long enough; close cycle no-op.")
        return
    snapshot_path = FORECASTS / f"{date_str}-close.json"
    if snapshot_path.exists():
        print("Immutable official snapshot already exists; close cycle no-op.")
        return
    system = read_json(DATA / "system.json")
    system["lastAttemptedCycle"] = iso(now)
    write_json(DATA / "system.json", system)
    try:
        frames = download_daily("5y")
        close, _ = align_panel(frames, ALL_SYMBOLS)
        latest_spy = pd.Timestamp(close[BENCHMARK].dropna().index[-1]).date()
        if latest_spy != now.date():
            raise RuntimeError(f"SPY daily data stale: latest {latest_spy}, expected {date_str}")
        track = resolve_forecasts(close)
        weights, weight_source, n_resolved = adaptive_weights(track)
        snapshot = build_forecast_snapshot(frames, date_str, weights)
        market_state = compute_market_state(close, date_str)
        propagation = compute_propagation(close, date_str)
        write_json(snapshot_path, snapshot)
        write_json(DATA / "current-forecasts.json", {
            "status": "live", "snapshotId": snapshot["snapshotId"], "path": str(snapshot_path.relative_to(ROOT)),
            "publishedAt": snapshot["publishedAt"], "sessionDate": date_str,
            "count": len(snapshot["forecasts"]), "forecasts": snapshot["forecasts"],
        })
        write_json(DATA / "market-state.json", market_state)
        write_json(DATA / "propagation.json", propagation)
        write_json(DATA / "track-record.json", track)
        model_state = read_json(DATA / "model-state.json")
        model_state.update({
            "status": "live", "weights": weights, "weightSource": weight_source,
            "liveResolvedPredictionCountUsedForWeights": n_resolved,
            "lastTrainedAt": snapshot["publishedAt"], "trainingWindow": snapshot["trainingRanges"],
        })
        write_json(DATA / "model-state.json", model_state)
        portfolio = read_json(DATA / "portfolio.json")
        candidates = [
            f for f in snapshot["forecasts"]
            if f["horizon"] == int(CONFIG["forecast"]["portfolioHorizon"])
            and f["pOutperform"] >= float(CONFIG["forecast"]["entryProbability"])
            and f["expectedExcessReturn"] >= float(CONFIG["forecast"]["entryExpectedExcessReturn"])
            and f["modelVotesOutperform"] >= 2
        ]
        candidates.sort(key=lambda f: (f["pOutperform"], f["expectedExcessReturn"]), reverse=True)
        held = {p["ticker"] for p in portfolio.get("positions", [])}
        pending = []
        for f in candidates:
            if f["ticker"] in held:
                continue
            pending.append({
                "ticker": f["ticker"], "sourceSnapshotId": snapshot["snapshotId"],
                "pOutperform": f["pOutperform"], "expectedExcessReturn": f["expectedExcessReturn"],
                "status": "planned", "reason": "Meets precommitted 5D entry threshold.",
            })
            if len(pending) >= int(CONFIG["portfolio"]["maxPositions"]):
                break
        portfolio["pendingEntries"] = pending
        held_prices = {s: float(close[s].dropna().iloc[-1]) for s in held if s in close and not close[s].dropna().empty}
        mark_portfolio(portfolio, held_prices, snapshot["publishedAt"])
        update_benchmark(portfolio, float(close[BENCHMARK].dropna().iloc[-1]))
        write_json(DATA / "portfolio.json", portfolio)
        system.update({
            "status": "live", "phase": "live-forward-experiment", "lastSuccessfulCycle": snapshot["publishedAt"],
            "lastError": None, "dataProvider": CONFIG["data"]["adapter"],
            "officialForecastCount": sum(len(read_json(p).get("forecasts", [])) for p in forecast_snapshots()),
            "resolvedForecastCount": track["metrics"]["resolvedCount"],
            "liveSince": system.get("liveSince") or snapshot["publishedAt"],
        })
        write_json(DATA / "system.json", system)
        write_json(STATES / f"{date_str}-close.json", {
            "cycle": "post-close", "at": snapshot["publishedAt"], "marketState": market_state,
            "forecastSnapshotId": snapshot["snapshotId"], "plannedEntries": pending,
        })
        print(f"Published {len(snapshot['forecasts'])} forecasts for {date_str}.")
    except Exception as exc:
        system["lastError"] = f"{type(exc).__name__}: {exc}"
        write_json(DATA / "system.json", system)
        raise


def fetch_intraday(symbols: list[str], prepost: bool = False) -> dict[str, pd.DataFrame]:
    if not symbols:
        return {}
    raw = yf.download(
        list(dict.fromkeys(symbols)), period="5d", interval="5m", auto_adjust=False,
        prepost=prepost, actions=False, group_by="ticker", threads=False, progress=False,
    )
    if raw.empty:
        return {}
    out = {}
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = set(raw.columns.get_level_values(0))
        for symbol in symbols:
            if symbol in level0:
                df = raw[symbol].copy().dropna(how="all")
                if not df.empty:
                    out[symbol] = df
    else:
        out[symbols[0]] = raw.copy().dropna(how="all")
    return out


def premarket_mode() -> None:
    now = now_et()
    date_str = now.date().isoformat()
    session = nyse_session(date_str)
    if session is None:
        print("No NYSE session today; premarket no-op.")
        return
    if now >= session["open"]:
        print(f"Missed premarket cutoff at {iso(session['open'])}; skipped without rewriting gates.")
        return
    portfolio = read_json(DATA / "portfolio.json")
    pending = portfolio.get("pendingEntries", [])
    symbols = [x["ticker"] for x in pending]
    refreshed, vetoes = [], []
    if symbols:
        intraday = fetch_intraday(symbols, prepost=True)
        daily = yf.download(symbols, period="5d", interval="1d", auto_adjust=False, group_by="ticker", threads=False, progress=False)
        for item in pending:
            symbol = item["ticker"]
            status, gap = "eligible", None
            try:
                prev = float(daily[symbol]["Close"].dropna().iloc[-1]) if isinstance(daily.columns, pd.MultiIndex) else float(daily["Close"].dropna().iloc[-1])
                df = intraday.get(symbol)
                if df is None or df.empty:
                    status = "veto-data-unavailable"
                else:
                    idx = df.index.tz_convert(TZ) if df.index.tz is not None else df.index.tz_localize(TZ)
                    mask = idx < pd.Timestamp(session["open"])
                    before = df.loc[mask]
                    if before.empty:
                        status = "veto-data-unavailable"
                    else:
                        last = float(before["Close"].dropna().iloc[-1])
                        gap = last / prev - 1.0
                        if abs(gap) >= float(CONFIG["portfolio"]["premarketAbsoluteGapVeto"]):
                            status = "veto-gap"
            except Exception:
                status = "veto-data-unavailable"
            row = {**item, "premarketStatus": status, "premarketGap": None if gap is None else round(float(gap), 6)}
            refreshed.append(row)
            if status != "eligible":
                vetoes.append({"ticker": symbol, "reason": status, "gap": row["premarketGap"]})
    pre = {
        "status": "live", "asOf": iso(now), "sessionDate": date_str, "marketOpen": iso(session["open"]),
        "plannedEntries": refreshed, "vetoes": vetoes,
        "note": "Premarket refresh never rewrites the prior close's official probabilities.",
    }
    portfolio["pendingEntries"] = refreshed
    write_json(DATA / "premarket.json", pre)
    write_json(DATA / "portfolio.json", portfolio)
    write_json(STATES / f"{date_str}-premarket.json", pre)
    print(f"Premarket refresh: {len(refreshed)} planned, {len(vetoes)} vetoed.")


def first_bar_typical_price(df: pd.DataFrame | None, session_date: str) -> float | None:
    if df is None or df.empty:
        return None
    idx = df.index.tz_convert(TZ) if df.index.tz is not None else df.index.tz_localize(TZ)
    target = pd.Timestamp(session_date).date()
    times = idx.time
    mask = (idx.date == target) & (times >= datetime.strptime("09:30", "%H:%M").time()) & (times < datetime.strptime("09:35", "%H:%M").time())
    candidates = df.loc[mask]
    if candidates.empty:
        return None  # A 09:35-labelled bar may be unfinished; never substitute it.
    row = candidates.iloc[0]
    vals = [float(row.get(k, np.nan)) for k in ["High", "Low", "Close"]]
    vals = [v for v in vals if np.isfinite(v) and v > 0]
    return None if not vals else float(np.mean(vals))


def execute_mode() -> None:
    now = now_et()
    date_str = now.date().isoformat()
    session = nyse_session(date_str)
    if session is None:
        print("No NYSE session today; execution no-op.")
        return
    if (STATES / f"{date_str}-execution.json").exists():
        print("Execution already recorded for this session; no duplicate execution.")
        return
    if now < session["open"] + timedelta(minutes=5):
        raise RuntimeError("first five-minute execution bar is not complete")
    if now > session["open"] + timedelta(minutes=15):
        missed = STATES / f"{date_str}-execution-missed.json"
        if not missed.exists():
            write_json(missed, {
                "cycle": "paper-execution-missed", "at": iso(now), "sessionDate": date_str,
                "reason": "GitHub scheduled run arrived after the 09:45 ET safety cutoff; no retrospective fills.",
            })
        print("Execution window missed; no trade or benchmark backfill.")
        return
    portfolio = read_json(DATA / "portfolio.json")
    current = read_json(DATA / "current-forecasts.json")
    if current.get("status") != "live":
        print("No prior official forecast; execution no-op.")
        return
    recent = mcal.get_calendar("NYSE").schedule(
        start_date=(now.date() - timedelta(days=10)).isoformat(),
        end_date=(now.date() - timedelta(days=1)).isoformat(),
    )
    previous_session = recent.index[-1].date().isoformat() if not recent.empty else None
    if current.get("sessionDate") != previous_session:
        print(f"No forecast from previous NYSE session ({previous_session}); execution no-op.")
        return
    premarket = read_json(DATA / "premarket.json")
    valid_premarket = (
        premarket.get("sessionDate") == date_str
        and premarket.get("status") == "live"
        and bool(premarket.get("asOf"))
        and pd.Timestamp(premarket["asOf"]).to_pydatetime() < session["open"]
    )
    pending = portfolio.get("pendingEntries", []) if valid_premarket else []
    if not valid_premarket:
        print("No valid same-session premarket risk check; new entries vetoed.")
    held = {p["ticker"]: p for p in portfolio.get("positions", [])}
    symbols = sorted(set(list(held) + [x["ticker"] for x in pending] + [BENCHMARK]))
    intraday = fetch_intraday(symbols, prepost=False)
    prices = {s: first_bar_typical_price(intraday.get(s), date_str) for s in symbols}
    if prices.get(BENCHMARK) is None:
        raise RuntimeError("SPY execution price unavailable")
    mark_portfolio(portfolio, {s: p for s, p in prices.items() if p is not None}, iso(now))
    equity_before = float(portfolio["equity"])
    forecast5 = {f["ticker"]: f for f in current.get("forecasts", []) if int(f["horizon"]) == int(CONFIG["forecast"]["portfolioHorizon"])}
    costs = float(CONFIG["portfolio"]["slippagePerSide"])
    trades = portfolio.setdefault("trades", [])
    kept = []
    for pos in portfolio.get("positions", []):
        f = forecast5.get(pos["ticker"])
        should_exit = f is not None and float(f["pOutperform"]) <= float(CONFIG["forecast"]["exitProbability"])
        if not should_exit:
            kept.append(pos)
            continue
        price = prices.get(pos["ticker"])
        if price is None:
            kept.append(pos)
            continue
        gross = float(pos["shares"]) * price
        cost = gross * costs
        portfolio["cash"] = round(float(portfolio["cash"]) + gross - cost, 6)
        trades.append({
            "id": f"{date_str}-{pos['ticker']}-SELL", "at": iso(now), "sessionDate": date_str,
            "ticker": pos["ticker"], "side": "SELL", "shares": pos["shares"],
            "executionPrice": round(price, 6), "notional": round(gross, 6), "syntheticCost": round(cost, 6),
            "reason": "5D probability crossed the precommitted exit threshold.", "sourceSnapshotId": current["snapshotId"],
        })
    portfolio["positions"] = kept
    slots = int(CONFIG["portfolio"]["maxPositions"]) - len(kept)
    eligible = [
        x for x in pending
        if x.get("premarketStatus") == "eligible"
        and x["ticker"] not in {p["ticker"] for p in kept}
    ]
    eligible.sort(key=lambda x: (x["pOutperform"], x["expectedExcessReturn"]), reverse=True)
    for item in eligible[:max(0, slots)]:
        ticker = item["ticker"]
        price = prices.get(ticker)
        if price is None or price <= 0:
            continue
        target_notional = equity_before * float(CONFIG["portfolio"]["maxPositionWeight"])
        notional = min(target_notional, max(0.0, float(portfolio["cash"])) / (1 + costs))
        if notional < 25:
            continue
        shares = notional / price
        cost = notional * costs
        portfolio["cash"] = round(float(portfolio["cash"]) - notional - cost, 6)
        pos = {
            "ticker": ticker, "shares": round(shares, 8), "entryPrice": round(price, 6), "entryAt": iso(now),
            "sourceSnapshotId": item["sourceSnapshotId"], "entryProbability": item["pOutperform"],
            "entryExpectedExcessReturn": item["expectedExcessReturn"], "lastPrice": round(price, 6), "marketValue": round(notional, 6),
        }
        portfolio["positions"].append(pos)
        trades.append({
            "id": f"{date_str}-{ticker}-BUY", "at": iso(now), "sessionDate": date_str,
            "ticker": ticker, "side": "BUY", "shares": round(shares, 8), "executionPrice": round(price, 6),
            "notional": round(notional, 6), "syntheticCost": round(cost, 6),
            "reason": "Frozen 5D entry rule passed and premarket veto did not trigger.", "sourceSnapshotId": item["sourceSnapshotId"],
        })
    portfolio["pendingEntries"] = []
    portfolio["status"] = "live"
    if portfolio["benchmark"].get("startedAt") is None:
        portfolio["benchmark"]["startedAt"] = iso(now)
        portfolio["benchmark"]["entryPrice"] = round(float(prices[BENCHMARK]), 6)
    update_benchmark(portfolio, prices[BENCHMARK])
    mark_portfolio(portfolio, {s: p for s, p in prices.items() if p is not None}, iso(now))
    write_json(DATA / "portfolio.json", portfolio)
    track = read_json(DATA / "track-record.json")
    port_ret = float(portfolio["equity"]) / float(portfolio["startingCash"]) - 1
    spy_ret = float(portfolio["benchmark"]["currentValue"]) / float(portfolio["benchmark"]["startingValue"]) - 1
    track["portfolio"] = {
        "return": round(port_ret, 8), "spyReturn": round(spy_ret, 8),
        "excessReturn": round(port_ret - spy_ret, 8), "tradeCount": len(trades),
    }
    track["updatedAt"] = iso(now)
    write_json(DATA / "track-record.json", track)
    write_json(STATES / f"{date_str}-execution.json", {
        "cycle": "paper-execution", "at": iso(now), "equity": portfolio["equity"], "cash": portfolio["cash"],
        "positions": portfolio["positions"], "tradesToday": [t for t in trades if t["sessionDate"] == date_str],
    })
    print(f"Execution complete: equity ${portfolio['equity']:.2f}; positions {len(portfolio['positions'])}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["premarket", "execute", "close"])
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    FORECASTS.mkdir(exist_ok=True)
    STATES.mkdir(exist_ok=True)
    if args.mode == "premarket":
        premarket_mode()
    elif args.mode == "execute":
        execute_mode()
    else:
        postclose_mode()


if __name__ == "__main__":
    main()
