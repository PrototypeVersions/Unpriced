"""Audit the *actual* NYSE cycle outcome without backfilling forecasts or fills.

This does not repair GitHub's best-effort scheduling. It records a same-session
miss only after the respective boundary, using the actual observation time.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("America/New_York")


def read_at(path: Path, field: str) -> datetime | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text()).get(field)
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        return None
    return result.astimezone(TZ) if result.tzinfo else None


def audit_missing(now: datetime, session: dict, states: Path) -> list[Path]:
    """Create missing *current-session* audit records, never alter existing ones."""
    if now.tzinfo is None:
        raise ValueError("Audit requires an offset-aware clock")
    now = now.astimezone(TZ)
    day = now.date().isoformat()
    market_open = session["open"].astimezone(TZ)
    created = []
    checks = (
        (
            "premarket",
            now >= market_open,
            read_at(states / f"{day}-premarket.json", "asOf"),
            lambda at: at < market_open,
            "No valid premarket refresh was recorded by the NYSE open; "
            "no retrospective eligibility.",
        ),
        (
            "execution",
            now > market_open + timedelta(minutes=15),
            read_at(states / f"{day}-execution.json", "at"),
            lambda at: market_open + timedelta(minutes=5) <= at <= market_open + timedelta(minutes=15),
            "No valid 09:35–09:45 ET paper execution was recorded by the "
            "cutoff; no retrospective fills or benchmark start.",
        ),
    )
    for kind, deadline_passed, recorded_at, timely, reason in checks:
        if not deadline_passed or (recorded_at is not None and timely(recorded_at)):
            continue
        missed = states / f"{day}-{kind}-missed.json"
        if missed.exists():
            continue
        states.mkdir(parents=True, exist_ok=True)
        content = {
            "cycle": "paper-execution-missed" if kind == "execution" else "premarket-missed",
            "at": now.isoformat(),
            "sessionDate": day,
            "reason": reason,
        }
        # An after-the-fact audit has an after-the-fact timestamp, never a fake cutoff time.
        with missed.open("x") as f:
            json.dump(content, f, indent=2)
            f.write("\n")
        created.append(missed)
    return created


def status_lines(now: datetime, session: dict, states: Path, forecasts: Path) -> tuple[list[str], list[str]]:
    day = now.date().isoformat()
    market_open = session["open"]
    settled = session["close"] + timedelta(minutes=35)
    pre = read_at(states / f"{day}-premarket.json", "asOf")
    execution = read_at(states / f"{day}-execution.json", "at")
    snapshot = forecasts / f"{day}-close.json"
    published = read_at(snapshot, "publishedAt")
    lines = [f"NYSE {day}, audited at {now.isoformat()} (actual ET clock)"]
    warnings = []

    if pre is not None and pre < market_open:
        lines.append(f"Premarket: valid at {pre.isoformat()} (target 08:45 ET)")
    elif (states / f"{day}-premarket-missed.json").exists():
        lines.append("Premarket: MISSED; see immutable dated miss record")
        warnings.append(f"{day}: no valid premarket refresh before the opening bell")
    else:
        lines.append("Premarket: not yet due")

    if execution is not None and market_open + timedelta(minutes=5) <= execution <= market_open + timedelta(minutes=15):
        lines.append(f"Paper execution: valid at {execution.isoformat()} (window 09:35–09:45 ET)")
    elif (states / f"{day}-execution-missed.json").exists():
        lines.append("Paper execution: MISSED; no backfilled trade or SPY start")
        warnings.append(f"{day}: paper execution missed 09:35–09:45 ET")
    else:
        lines.append("Paper execution: not yet due")

    if snapshot.exists():
        if published is None:
            lines.append("Forecast: INVALID publication timestamp")
            warnings.append(f"{day}: dated forecast lacks a valid publication timestamp")
        elif published < settled:
            lines.append(f"Forecast: INVALID {published.isoformat()}, before 35-minute settlement")
            warnings.append(f"{day}: forecast timestamp precedes the settlement boundary")
        else:
            lag = int((published - settled).total_seconds())
            lines.append(
                f"Forecast: published {published.isoformat()}, "
                f"{lag // 60}m {lag % 60}s after {settled.strftime('%H:%M')} ET target"
            )
            if lag > 600:
                warnings.append(f"{day}: forecast published more than 10 minutes after close+35m")
    elif now >= settled:
        lines.append("Forecast: MISSING after required 35-minute settlement buffer")
        warnings.append(f"{day}: no dated close forecast after settlement boundary")
    else:
        lines.append(f"Forecast: not yet due (earliest {settled.strftime('%H:%M')} ET)")
    return lines, warnings


def main() -> None:
    now = datetime.now(TZ)
    day = now.date().isoformat()
    sched = mcal.get_calendar("NYSE").schedule(start_date=day, end_date=day)
    if sched.empty:
        print(f"No NYSE session on {day}; no current-session audit.")
        return
    session = {
        "open": sched.iloc[0]["market_open"].tz_convert(TZ).to_pydatetime(),
        "close": sched.iloc[0]["market_close"].tz_convert(TZ).to_pydatetime(),
    }
    states = ROOT / "states"
    created = audit_missing(now, session, states)
    lines, warnings = status_lines(now, session, states, ROOT / "forecasts")
    for item in created:
        print(f"Recorded observed miss (never backdated): {item.relative_to(ROOT)}")
    for line in lines:
        print(line)
    for issue in warnings:
        print(f"::warning::{issue}")
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("### Market-cycle outcome (not merely workflow success)\n\n")
            for line in lines:
                f.write(f"- {line}\n")
            f.write("\n")


if __name__ == "__main__":
    main()
