#!/usr/bin/env python3
"""
Day 2026-09-15 — GVU prototype
Opportunity: uncalibrated PPG glucose band + Clarke-zone safety layer
(inspired by GlucoNet / IoMT wearable, Smart Health 2023).

Generator: naive last-PPG-amplitude → mg/dL draft (often Zone C).
Verifier: Clarke-style zones vs a fingerstick reference; FAIL if Zone C/D/E
          OR if the draft uses meal-time calibration (paper is meal-agnostic).
Updater:  blend amplitude with perfusion index + pulse rate; drop meal term.

Not a medical device. Educational prototype only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Sample:
    """Synthetic wearable window + one reference fingerstick (mg/dL)."""

    ppg_ac_dc: float
    pulse_bpm: float
    motion_rms: float
    last_meal_min: int
    reference_mgdl: float


def clarke_zone(ref: float, pred: float) -> str:
    """Simplified Clarke Error Grid (A/B acceptable; C/D/E fail)."""
    if ref <= 0 or pred <= 0:
        return "E"
    if abs(pred - ref) / ref <= 0.20:
        return "A"
    if ref < 70 and pred < 70:
        return "A"
    if (ref >= 70 and pred >= 70) and abs(pred - ref) / ref <= 0.40:
        return "B"
    if ref < 70 and pred >= 90:
        return "D"
    if ref > 180 and pred < 70:
        return "D"
    if ref < 70 and pred > 180:
        return "E"
    if ref > 240 and pred < 70:
        return "E"
    return "C"


@dataclass
class Draft:
    estimated_mgdl: float
    used_meal_time: bool
    features: list[str]
    note: str


def generate(sample: Sample, critique: str | None = None) -> Draft:
    if critique is None:
        est = 80.0 + sample.ppg_ac_dc * 180.0
        if sample.last_meal_min < 90:
            est += 45.0
        return Draft(
            estimated_mgdl=round(est, 1),
            used_meal_time=True,
            features=["ppg_ac_dc", "last_meal_min"],
            note="naive amplitude + meal lag",
        )
    base = 70.0 + sample.ppg_ac_dc * 140.0
    hr_term = (sample.pulse_bpm - 72.0) * 0.35
    motion_penalty = sample.motion_rms * 8.0
    est = base + hr_term - motion_penalty
    est = max(55.0, min(est, 260.0))
    return Draft(
        estimated_mgdl=round(est, 1),
        used_meal_time=False,
        features=["ppg_ac_dc", "pulse_bpm", "motion_rms"],
        note="meal-agnostic multi-feature revision",
    )


def verify(draft: Draft, sample: Sample) -> dict[str, Any]:
    zone = clarke_zone(sample.reference_mgdl, draft.estimated_mgdl)
    reasons: list[str] = []
    ok = True
    if zone in {"C", "D", "E"}:
        ok = False
        reasons.append(f"Clarke zone {zone} is not clinically acceptable (need A or B)")
    if draft.used_meal_time:
        ok = False
        reasons.append("used last_meal_min — violates meal/time-agnostic GlucoNet constraint")
    if len(draft.features) < 2:
        ok = False
        reasons.append("must cite at least two PPG/physio features")
    if not reasons:
        reasons.append(f"pass: zone {zone}, meal-agnostic, features={draft.features}")
    return {"pass": ok, "zone": zone, "reasons": reasons}


def run_gvu(sample: Sample, max_passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: str | None = None
    draft = generate(sample, critique)
    for i in range(1, max_passes + 1):
        verdict = verify(draft, sample)
        log.append({"pass": i, "draft": asdict(draft), "verdict": verdict})
        if verdict["pass"]:
            break
        critique = "; ".join(verdict["reasons"])
        draft = generate(sample, critique)
    return log


def main() -> None:
    sample = Sample(
        ppg_ac_dc=0.42,
        pulse_bpm=88.0,
        motion_rms=0.15,
        last_meal_min=40,
        reference_mgdl=118.0,
    )
    log = run_gvu(sample)
    print("SAMPLE", asdict(sample))
    print("BEFORE (pass 1):", json.dumps(log[0], indent=2))
    print("AFTER  (last pass):", json.dumps(log[-1], indent=2))
    print("PASSES:", len(log), "FINAL_PASS:", log[-1]["verdict"]["pass"])


if __name__ == "__main__":
    main()
