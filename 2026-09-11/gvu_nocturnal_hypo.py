#!/usr/bin/env python3
"""
Day 2026-09-11 — Nocturnal hypoglycemia 7-hour risk flag
Generator–Verifier–Updater loop.

Insight prototyped: evening CGM slope + variability + time-below-80
should jointly drive a 7-hour Night Low Predict flag — not last-point alone.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List


# Synthetic evening window (mg/dL), 5-min samples 21:00–22:30
SAMPLE_WINDOW = [118, 114, 109, 104, 98, 94, 91, 88, 86, 84, 82, 80, 78, 76, 75, 74, 73, 72]


@dataclass
class Draft:
    risk: str  # LOW | MEDIUM | HIGH
    predicted_nadir_mgdl: float
    reasons: List[str]
    pass_id: int


def slope(window: List[float]) -> float:
    if len(window) < 2:
        return 0.0
    return (window[-1] - window[0]) / (len(window) - 1)


def cv_pct(window: List[float]) -> float:
    mean = sum(window) / len(window)
    var = sum((x - mean) ** 2 for x in window) / len(window)
    return 100.0 * (var ** 0.5) / mean if mean else 0.0


def minutes_below(window: List[float], thresh: float, dt_min: int = 5) -> int:
    return sum(1 for x in window if x < thresh) * dt_min


def generate(window: List[float], critique: str | None, pass_id: int) -> Draft:
    last = window[-1]
    s = slope(window)
    if critique is None:
        if last < 70:
            risk, nadir = "HIGH", last - 5
            reasons = [f"last reading {last} mg/dL < 70"]
        elif last < 90:
            risk, nadir = "MEDIUM", last - 8
            reasons = [f"last reading {last} mg/dL in 70–90"]
        else:
            risk, nadir = "LOW", last - 10
            reasons = [f"last reading {last} mg/dL looks safe"]
        return Draft(risk, nadir, reasons, pass_id)

    tb80 = minutes_below(window, 80)
    c = cv_pct(window)
    projected = last + s * (7 * 60 / 5)
    nadir = max(40.0, min(last, projected))
    reasons = [
        f"last={last:.0f}",
        f"slope={s:.2f} mg/dL per 5min",
        f"TB80={tb80} min",
        f"CV={c:.1f}%",
        f"7h-extrap={projected:.0f}",
        f"critique={critique[:80]}",
    ]
    if projected < 54 or (s < -1.0 and last < 85):
        risk = "HIGH"
    elif projected < 70 or tb80 >= 20:
        risk = "HIGH" if last < 80 else "MEDIUM"
    elif last < 90 and s < 0:
        risk = "MEDIUM"
    else:
        risk = "LOW"
    return Draft(risk, nadir, reasons, pass_id)


def verify(draft: Draft, window: List[float]) -> tuple[bool, str]:
    """
    Success criterion (falsifiable):
    If evening slope < -0.5 mg/dL per 5 min AND last < 80 AND TB80 >= 15 min,
    risk MUST be HIGH. Last-point-only MEDIUM/LOW is a fail.
    """
    last = window[-1]
    s = slope(window)
    tb80 = minutes_below(window, 80)
    triggered = s < -0.5 and last < 80 and tb80 >= 15
    if triggered and draft.risk != "HIGH":
        return False, (
            f"FAIL: downward evening trend (slope={s:.2f}, last={last}, TB80={tb80}min) "
            f"requires HIGH 7-hour nocturnal risk, got {draft.risk}."
        )
    if draft.predicted_nadir_mgdl > last + 5 and s < 0:
        return False, "FAIL: predicted nadir cannot rise while slope is negative."
    return True, f"PASS: risk={draft.risk} matches nocturnal-trend rule."


def run_gvu(window: List[float], max_passes: int = 3) -> list[Draft]:
    logs: list[Draft] = []
    critique = None
    for i in range(1, max_passes + 1):
        draft = generate(window, critique, i)
        ok, msg = verify(draft, window)
        draft.reasons.append(msg)
        logs.append(draft)
        print(f"--- pass {i} ---")
        print(asdict(draft))
        print(msg)
        if ok:
            break
        critique = msg
    return logs


if __name__ == "__main__":
    print("Sample evening window:", SAMPLE_WINDOW)
    print("slope:", round(slope(SAMPLE_WINDOW), 3), "TB80:", minutes_below(SAMPLE_WINDOW, 80))
    run_gvu(SAMPLE_WINDOW)
