#!/usr/bin/env python3
"""Synchronize machine-owned documentation snapshots with canonical repo state.

This script intentionally updates only text between AUTO-SNAPSHOT markers.
Narrative design rationale remains manually maintained.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER_START = "<!-- AUTO-SNAPSHOT:START -->"
MARKER_END = "<!-- AUTO-SNAPSHOT:END -->"
TARGETS = [
    ROOT / "docs" / "AI_HANDOFF.md",
    ROOT / "docs" / "MODEL_CARD_V1.md",
    ROOT / "docs" / "ROADMAP.md",
]


def read_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def pct(x: float) -> str:
    return f"{100 * float(x):.1f}%"


def build_snapshot() -> str:
    config = read_json(ROOT / "config.json", {})
    system = read_json(ROOT / "data" / "system.json", {})

    schedule = config.get("schedule", {})
    forecast = config.get("forecast", {})
    portfolio = config.get("portfolio", {})
    learning = config.get("learning", {})
    data = config.get("data", {})

    close_snapshots = sorted((ROOT / "forecasts").glob("*-close.json")) if (ROOT / "forecasts").exists() else []
    snapshot_days = len(close_snapshots)

    resolved = int(system.get("resolvedForecastCount") or 0)
    official = int(system.get("officialForecastCount") or 0)
    adaptive_threshold = int(learning.get("adaptiveWeightingStartsAfterResolvedPredictions") or 100)
    v2_threshold_days = 20

    if snapshot_days >= v2_threshold_days:
        v2_status = f"checkpoint reached ({snapshot_days} immutable close snapshots; ≥ {v2_threshold_days})"
    else:
        v2_status = f"not yet reached ({snapshot_days}/{v2_threshold_days} immutable close snapshots)"

    if resolved >= adaptive_threshold:
        adaptive_status = f"eligible ({resolved}/{adaptive_threshold} resolved live predictions)"
    else:
        adaptive_status = f"frozen initial weights ({resolved}/{adaptive_threshold} resolved live predictions)"

    weights = learning.get("initialModelWeights", {})
    weight_text = ", ".join(f"`{k}` {pct(v)}" for k, v in weights.items()) or "not configured"

    horizons = ", ".join(str(h) for h in forecast.get("horizons", [])) or "not configured"
    universe_count = len(config.get("universe", []))
    context_count = len(config.get("contextSymbols", []))

    status = system.get("status", config.get("status", "unknown"))
    phase = system.get("phase", "unknown")
    live_since = system.get("liveSince") or "not yet live"
    last_success = system.get("lastSuccessfulCycle") or "none yet"
    last_error = system.get("lastError") or "none"

    lines = [
        MARKER_START,
        "## Automated current snapshot",
        "",
        "_Generated from `config.json`, `data/system.json`, and immutable files under `forecasts/`. Do not hand-edit this block._",
        "",
        f"- **System status:** `{status}`; phase `{phase}`; live since: {live_since}.",
        f"- **Last successful cycle:** {last_success}; **last recorded error:** {last_error}.",
        f"- **Forward record:** {snapshot_days} immutable close snapshots; {official} official forecast observations; {resolved} resolved live observations.",
        f"- **V2 development checkpoint:** {v2_status}.",
        f"- **Adaptive ensemble status:** {adaptive_status}.",
        f"- **Official schedule (America/New_York):** premarket {schedule.get('premarketRefresh', '—')}; paper execution {schedule.get('paperExecution', '—')}; normal close {schedule.get('postCloseForecast', '—')}; early close {schedule.get('earlyCloseForecast', '—')}.",
        f"- **Forecast target:** relative to `{forecast.get('benchmark', 'SPY')}` at {horizons} trading-session horizons; website display minimum {pct(forecast.get('displayMinimumProbability', 0))}.",
        f"- **Portfolio gates:** entry probability ≥ {pct(forecast.get('entryProbability', 0))}; exit probability ≤ {pct(forecast.get('exitProbability', 0))}; expected excess-return entry floor {pct(forecast.get('entryExpectedExcessReturn', 0))}.",
        f"- **Portfolio:** starting cash ${float(portfolio.get('startingCash', 0)):,.0f}; max {portfolio.get('maxPositions', '—')} positions; max position weight {pct(portfolio.get('maxPositionWeight', 0))}; cost/slippage {pct(portfolio.get('slippagePerSide', 0))} per side; overnight new-entry veto {pct(portfolio.get('premarketAbsoluteGapVeto', 0))} absolute gap.",
        f"- **Learning:** rolling {learning.get('rollingTrainingYears', '—')}-year training window; initial weights {weight_text}; adaptive lookback up to {learning.get('adaptiveLookbackResolvedPredictions', '—')} resolved live predictions; weight floor {pct(learning.get('weightFloor', 0))}; cap {pct(learning.get('weightCap', 0))}.",
        f"- **Coverage:** {universe_count} forecast-universe equities plus {context_count} market/context symbols.",
        f"- **Data adapter:** `{data.get('adapter', system.get('dataProvider', 'unknown'))}`; fail closed: `{bool(data.get('failClosed', False))}`.",
        MARKER_END,
    ]
    return "\n".join(lines)


def replace_snapshot(text: str, snapshot: str) -> str:
    if MARKER_START not in text or MARKER_END not in text:
        raise RuntimeError("Missing AUTO-SNAPSHOT markers")
    before, rest = text.split(MARKER_START, 1)
    _, after = rest.split(MARKER_END, 1)
    return before.rstrip() + "\n\n" + snapshot + "\n" + after.lstrip("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit nonzero if generated blocks are stale")
    args = parser.parse_args()

    snapshot = build_snapshot()
    stale = []

    for path in TARGETS:
        old = path.read_text(encoding="utf-8")
        new = replace_snapshot(old, snapshot)
        if old != new:
            stale.append(path)
            if not args.check:
                path.write_text(new, encoding="utf-8")

    if args.check and stale:
        print("Documentation snapshot is stale:")
        for path in stale:
            print(f" - {path.relative_to(ROOT)}")
        return 1

    if stale and not args.check:
        print("Updated:")
        for path in stale:
            print(f" - {path.relative_to(ROOT)}")
    else:
        print("Documentation snapshot already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
