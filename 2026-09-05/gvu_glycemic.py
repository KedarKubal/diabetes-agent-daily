#!/usr/bin/env python3
"""Generator–Verifier–Updater glycemic risk prototype (Day 2026-09-05).

Educational / research only. Not a medical device.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import List


SAMPLE = {
    "patient_id": "demo-01",
    "cgm_mg_dl": [92, 84, 71, 66, 63],  # falling toward hypo
    "insulin_on_board_u": 2.4,
    "minutes_since_meal": 180,
    "activity": "walk_after_dinner",
}


HYPO_MG = 70
TARGET_LOW, TARGET_HIGH = 70, 180


@dataclass
class Draft:
    risk_score: int
    hypo_flag: bool
    next_glucose_est: float
    time_in_range_pct: float
    nudge: str
    notes: str


def _slope(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    return (vals[-1] - vals[0]) / max(len(vals) - 1, 1)


def generate(sample: dict, critique: str | None = None) -> Draft:
    vals = [float(x) for x in sample["cgm_mg_dl"]]
    last = vals[-1]
    sl = _slope(vals)
    iob = float(sample.get("insulin_on_board_u", 0))
    minutes = float(sample.get("minutes_since_meal", 240))

    next_est = last + sl * 2 - 4.0 * iob
    if minutes > 150:
        next_est -= 3.0

    # First pass is naive (uses only last point) so Verifier can fail and loop can improve.
    use_window = critique is not None
    if critique:
        if "underflag" in critique.lower() or "missed hypo" in critique.lower():
            next_est -= 8.0
            use_window = True

    if use_window:
        hypo = last < HYPO_MG or next_est < HYPO_MG or min(vals[-3:]) < HYPO_MG
    else:
        hypo = last < 55  # naive generator misses 63–69 mg/dL

    in_range = sum(1 for v in vals if TARGET_LOW <= v <= TARGET_HIGH) / len(vals)
    risk = int(max(0, min(100, (HYPO_MG - min(last, next_est)) * 3 + iob * 8 + abs(min(sl, 0)) * 4)))
    if not hypo:
        risk = min(risk, 35)

    if hypo:
        nudge = (
            "Hypoglycemia risk: pause extra insulin, take 15g fast carb if "
            "symptomatic or if next reading stays <70, recheck in 15 min."
        )
        notes = "Falling CGM + residual IOB. Do not describe as stable."
    else:
        nudge = "Stay in range: protein snack if a long gap since last meal; walk is fine."
        notes = "No current hypo flag."

    if critique and hypo:
        nudge += " Verifier-adjusted: treat last reading as actionable now."

    return Draft(
        risk_score=risk,
        hypo_flag=hypo,
        next_glucose_est=round(next_est, 1),
        time_in_range_pct=round(100 * in_range, 1),
        nudge=nudge,
        notes=notes,
    )


def verify(draft: Draft, sample: dict) -> dict:
    vals = [float(x) for x in sample["cgm_mg_dl"]]
    reasons = []
    fail = False

    must_flag = min(vals[-3:]) < HYPO_MG
    if must_flag and not draft.hypo_flag:
        fail = True
        reasons.append("missed hypo: last-3 window contains <70 mg/dL (underflag)")

    if draft.hypo_flag and "stable" in draft.nudge.lower():
        fail = True
        reasons.append("contradict: hypo_flag true but nudge says stable")

    if not (0 <= draft.risk_score <= 100):
        fail = True
        reasons.append("risk_score out of 0-100")

    if draft.time_in_range_pct is None:
        fail = True
        reasons.append("missing TIR")

    if must_flag and draft.risk_score < 40:
        fail = True
        reasons.append("risk_score too low given confirmed hypo window")

    if not reasons:
        reasons.append("all explicit criteria passed")

    return {"pass": not fail, "reasons": reasons}


def run_loop(sample: dict, max_passes: int = 3) -> list:
    log = []
    critique = None
    draft = None
    for i in range(1, max_passes + 1):
        draft = generate(sample, critique)
        verdict = verify(draft, sample)
        rec = {
            "pass": i,
            "draft": asdict(draft),
            "verdict": verdict,
        }
        log.append(rec)
        if verdict["pass"]:
            break
        critique = "; ".join(verdict["reasons"])
    return log


def main():
    log = run_loop(SAMPLE, 3)
    print("=== SAMPLE INPUT ===")
    print(json.dumps(SAMPLE, indent=2))
    print("\n=== GVU LOG ===")
    print(json.dumps(log, indent=2))
    print("\n=== BEFORE (pass 1) vs AFTER (last pass) ===")
    print("BEFORE:", json.dumps(log[0]["draft"], indent=2))
    print("AFTER :", json.dumps(log[-1]["draft"], indent=2))
    print("FINAL VERDICT:", log[-1]["verdict"])


if __name__ == "__main__":
    main()
