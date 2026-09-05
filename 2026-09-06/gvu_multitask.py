#!/usr/bin/env python3
"""Day 2026-09-06 GVU prototype: multi-task 30-min glucose forecast + hypo flag.

Insight prototyped (Hwang et al., NPJ Digit Med 2025): one model should jointly
forecast glucose AND classify hypoglycemia so the two outputs stay consistent
(Sim2Real multi-task). Generator is naive; Verifier enforces physiology +
consistency; Updater revises 3 passes.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List
import json


SAMPLE_CGM = [118.0, 108.0, 98.0, 90.0, 82.0]  # falling fast, last still >70
HORIZON_MIN = 30
MAX_RATE = 3.0  # mg/dL per minute, conservative physiologic bound
HYPO_MGDL = 70.0


@dataclass
class Candidate:
    forecast_mgdl: float
    hypo_flag: bool
    note: str


def slope_per_min(window: List[float]) -> float:
    if len(window) < 2:
        return 0.0
    dt = 5.0 * (len(window) - 1)
    return (window[-1] - window[0]) / dt


def generate(window: List[float], critique: str | None = None) -> Candidate:
    last = window[-1]
    s = slope_per_min(window)
    forecast = last + s * HORIZON_MIN
    hypo = last < HYPO_MGDL
    note = "linear-extrap last-point-flag"
    if critique:
        max_delta = MAX_RATE * HORIZON_MIN
        forecast = max(last - max_delta, min(last + max_delta, forecast))
        falling = s < -0.2
        if falling and last < 80:
            hypo = True
        if forecast < HYPO_MGDL:
            hypo = True
        if forecast >= 80 and s >= 0:
            hypo = False
        note = f"revised-from-critique:{critique[:80]}"
    return Candidate(round(forecast, 2), hypo, note)


def verify(window: List[float], cand: Candidate) -> tuple[bool, str]:
    last = window[-1]
    s = slope_per_min(window)
    reasons = []

    delta = abs(cand.forecast_mgdl - last)
    if delta > MAX_RATE * HORIZON_MIN + 1e-6:
        reasons.append(
            f"forecast change {delta:.1f} exceeds max {MAX_RATE * HORIZON_MIN:.0f} mg/dL in {HORIZON_MIN} min"
        )

    if cand.forecast_mgdl < HYPO_MGDL and not cand.hypo_flag:
        reasons.append("inconsistent: forecast < 70 but hypo_flag is False")
    if cand.forecast_mgdl >= 80 and s >= 0 and cand.hypo_flag:
        reasons.append("inconsistent: rising/stable forecast >= 80 but hypo_flag is True")

    falling = s < -0.2
    if falling and last < 80 and not cand.hypo_flag:
        reasons.append("missed impending hypo: falling slope and last < 80")

    if last < HYPO_MGDL and not cand.hypo_flag:
        reasons.append("already below 70 but hypo_flag is False")

    if reasons:
        return False, "; ".join(reasons)
    return True, "pass: physiologic rate + multi-task consistency"


def run_gvu(window: List[float], passes: int = 3) -> list[dict]:
    log = []
    critique = None
    for i in range(1, passes + 1):
        cand = generate(window, critique)
        ok, reason = verify(window, cand)
        log.append(
            {
                "pass": i,
                "candidate": asdict(cand),
                "pass_fail": "PASS" if ok else "FAIL",
                "verifier": reason,
            }
        )
        if ok:
            break
        critique = reason
    return log


def main() -> None:
    print("SAMPLE CGM window (5-min spacing):", SAMPLE_CGM)
    print("slope mg/dL/min:", round(slope_per_min(SAMPLE_CGM), 3))
    log = run_gvu(SAMPLE_CGM, passes=3)
    print(json.dumps(log, indent=2))
    print("\nBEFORE (pass 1):", log[0]["candidate"], log[0]["pass_fail"])
    print("AFTER  (last):  ", log[-1]["candidate"], log[-1]["pass_fail"])


if __name__ == "__main__":
    main()
