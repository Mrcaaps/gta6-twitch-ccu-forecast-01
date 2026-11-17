"""gta6-twitch-ccu-forecast-01 entry in Python 3.13 (standard library only).

Forecasts the release day's Twitch viewers for hours 2..24 from hour 1's print
and the case's comparables: past big launches' hourly curves.

Model (validated by leave-one-out cross-validation over the case's own
comparables; see loo.py): for each comparable with a full release day, take its
log-ratio curve r_h = ln(v_h) - ln(v_1) for h = 2..24. The shape is not flat:
rolling-midnight launches dip after hour 1, rise as the US unlocks (hours 6
and 9), peak in the evening and fall off. For each hour, the forecast's five
quantiles are the weighted quantiles of r_h across comparables, weighted by
how similar the comparable's hour-1 size is to the target's (Gaussian kernel
on ln(v_1), bandwidth 1.0 log units) with a x3 bonus for rolling-midnight
unlocks (the target's unlock type). The forecast is q_tau(h) = p1 *
exp(quantile_tau(r_h)), p1 the target's hour-1 print. Everything is computed
at runtime from the case file's comparables; nothing is hardcoded from the
practice cases. Deterministic: no randomness, no wall clock, no network.

Fallback: if no comparable has a usable full release day, the persistence
baseline (starter) is used so the case still validates.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so `import model`
# finds a model.py shipped beside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level (persistence fallback only).
Z = [-1.645, -0.674, 0, 0.674, 1.645]
# Persistence fallback's spread, in log units per square-root hour.
SIGMA = 0.15
# Gaussian kernel bandwidth on ln(hour-1 viewers), in log units.
BANDWIDTH = 1.0
# Weight multiplier for rolling-midnight unlocks (the target's unlock type).
ROLLING_BONUS = 3.0


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as JavaScript's Math.round(x * 100) / 100.

    A whole number comes back as an int, so json.dumps writes 1240 where
    JavaScript writes 1240 (not 1240.0).
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_rolling(unlock: str) -> bool:
    """True when the unlock text says midnight-local rolling unlock."""
    u = (unlock or "").lower()
    if "single global" in u or "single simultaneous" in u or "simultaneous across" in u:
        return False
    if "simultaneous" in u and "midnight" not in u:
        return False
    return "midnight local" in u or "rolling" in u or "midnight" in u


def release_day_values(comp: dict) -> list[float] | None:
    """The comparable's release-day hourly viewers, hours 1..24, or None when
    the day is not fully covered with positive counts (e.g. the GTA VI
    category's own pre-release history, which has no release day yet)."""
    try:
        day_start = parse_time(comp["day_start"])
    except (KeyError, ValueError):
        return None
    by_hour: dict[int, float] = {}
    for row in comp.get("hourly") or []:
        try:
            at = parse_time(row["from"])
            viewers = row["viewers"]
        except (KeyError, ValueError, TypeError):
            continue
        if viewers is None:
            continue
        h = int((at - day_start).total_seconds() // 3600) + 1
        if 1 <= h <= 24 and h not in by_hour:
            by_hour[h] = viewers
    if len(by_hour) != 24:
        return None
    vals = [by_hour[h] for h in range(1, 25)]
    if any(v is None or v <= 0 for v in vals):
        return None
    return vals


def weighted_quantile(pairs: list[tuple[float, float]], tau: float) -> float:
    """Linear-interpolation quantile of values weighted by their weights.

    pairs: list of (value, weight). Sorted by value; the target is tau of the
    total weight, interpolated between neighbouring values.
    """
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    if total <= 0:
        return pairs[len(pairs) // 2][0]
    target = tau * total
    acc = 0.0
    for i, (v, w) in enumerate(pairs):
        prev = acc
        acc += w
        if acc >= target:
            if i == 0 or w == 0:
                return v
            frac = (target - prev) / w
            return pairs[i - 1][0] * (1 - frac) + v * frac
    return pairs[-1][0]


def hour_quantiles(p1: float, per_hour: dict[int, list[tuple[float, float]]],
                   h: int) -> list[float | int]:
    """The five quantiles for hour h from the comparables' log-ratio curves."""
    rs = per_hour[h]
    out = []
    for tau in LEVELS:
        r = weighted_quantile(rs, tau)
        q = p1 * math.exp(r)
        q = min(max(q, 1.0), 1_000_000_000.0)
        out.append(round2(q))
    # Enforce non-decreasing (float ties after rounding).
    for i in range(1, len(out)):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def persistence_quantiles(p1: float, h: int) -> list[float | int]:
    """The starter baseline's row for hour h (fallback when no comparable
    is usable)."""
    out = [round2(p1 * math.exp(z * SIGMA * math.sqrt(h - 1))) for z in Z]
    for i in range(1, len(out)):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    log_p1 = math.log(p1)

    # Per hour, the (log-ratio, weight) pairs across usable comparables.
    per_hour: dict[int, list[tuple[float, float]]] = {h: [] for h in range(2, 25)}
    for comp in case.get("comparables") or []:
        vals = release_day_values(comp)
        if vals is None:
            continue
        w = math.exp(-0.5 * ((math.log(vals[0]) - log_p1) / BANDWIDTH) ** 2)
        if is_rolling(comp.get("unlock", "")):
            w *= ROLLING_BONUS
        log_v1 = math.log(vals[0])
        for h in range(2, 25):
            per_hour[h].append((math.log(vals[h - 1]) - log_v1, w))

    hours = []
    for row in case["forecast"]:
        h = row["hour"]
        if per_hour[h]:
            q = hour_quantiles(p1, per_hour, h)
        else:
            q = persistence_quantiles(p1, h)
        hours.append({"hour": h, "q": q})
    return {"hours": hours}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
