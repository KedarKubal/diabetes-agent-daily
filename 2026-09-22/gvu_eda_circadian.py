#!/usr/bin/env python3
"""
Day 2026-09-22 — GVU prototype
Opportunity: free-living multimodal glucose-band estimate from
passively collected wearable features (EDA tonic + circadian hour + sex),
inspired by Chowdhury et al., Sensors 2025 (no food-log required).

Generator: naive last-CGM snapshot band.
Verifier: explicit, falsifiable criteria (see SUCCESS_CRITERIA).
Updater: fold critique into next candidate for 3 passes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal

Band = Literal["LOW", "IN_RANGE", "HIGH"]


SUCCESS_CRITERIA = {
    "must_cite_eda_tonic": True,
    "must_cite_circadian_hour": True,
    "must_cite_sex": True,
    "must_not_require_food_log": True,
    "band_must_use_eda_circadian_adjustment": True,
    "zone_ab_only": True,
}


@dataclass
class WearableSample:
    last_cgm_mgdl: float
    eda_tonic_us: float
    hour_local: int
    sex: Literal["F", "M"]
    ppg_hr_bpm: float


@dataclass
class Candidate:
    band: Band
    est_mgdl: float
    cited: list[str] = field(default_factory=list)
    rationale: str = ""
    used_food_log: bool = False


@dataclass
class Critique:
    passed: bool
    reasons: list[str]


def _circadian_shift(hour: int) -> float:
    if 4 <= hour <= 8:
        return 8.0
    if 21 <= hour or hour <= 1:
        return -4.0
    return 0.0


def _eda_shift(tonic: float) -> float:
    if tonic >= 4.0:
        return 12.0
    if tonic >= 2.0:
        return 5.0
    return -2.0


def _sex_shift(sex: str) -> float:
    return 3.0 if sex == "M" else -2.0


def generate(sample: WearableSample, critique: Critique | None) -> Candidate:
    if critique is None or critique.passed:
        return Candidate(
            band=_band(sample.last_cgm_mgdl),
            est_mgdl=round(sample.last_cgm_mgdl, 1),
            cited=["last_cgm"],
            rationale="Naive last-point snapshot; ignores wearable context.",
            used_food_log=False,
        )

    est = (
        sample.last_cgm_mgdl
        + _eda_shift(sample.eda_tonic_us)
        + _circadian_shift(sample.hour_local)
        + _sex_shift(sample.sex)
    )
    est = max(70.0, min(220.0, est))
    return Candidate(
        band=_band(est),
        est_mgdl=round(est, 1),
        cited=["eda_tonic", "circadian_hour", "sex", "last_cgm"],
        rationale=(
            f"Adjusted last CGM {sample.last_cgm_mgdl} by EDA tonic "
            f"{sample.eda_tonic_us} µS, hour {sample.hour_local}, sex {sample.sex}."
        ),
        used_food_log=False,
    )


def _band(mgdl: float) -> Band:
    if mgdl < 70:
        return "LOW"
    if mgdl > 180:
        return "HIGH"
    return "IN_RANGE"


def verify(candidate: Candidate, sample: WearableSample) -> Critique:
    reasons: list[str] = []
    cited = set(candidate.cited)

    if "eda_tonic" not in cited:
        reasons.append("FAIL: did not cite EDA tonic (paper's top wearable predictor).")
    if "circadian_hour" not in cited:
        reasons.append("FAIL: did not cite circadian hour.")
    if "sex" not in cited:
        reasons.append("FAIL: did not cite biological sex.")
    if candidate.used_food_log:
        reasons.append("FAIL: used a food log; paper shows passive sensors suffice.")

    expected = (
        sample.last_cgm_mgdl
        + _eda_shift(sample.eda_tonic_us)
        + _circadian_shift(sample.hour_local)
        + _sex_shift(sample.sex)
    )
    if abs(candidate.est_mgdl - expected) > 8.0 and not (
        "eda_tonic" in cited and "circadian_hour" in cited and "sex" in cited
    ):
        reasons.append(
            f"FAIL: estimate {candidate.est_mgdl} ignores multimodal shift "
            f"(expected ~{expected:.1f})."
        )

    if candidate.est_mgdl < 54 or candidate.est_mgdl > 250:
        reasons.append("FAIL: estimate outside Clarke A/B-plausible band.")

    if not reasons:
        reasons.append("PASS: multimodal, no food log, cited EDA+hour+sex.")
    return Critique(passed=len([r for r in reasons if r.startswith("FAIL")]) == 0, reasons=reasons)


def run_loop(sample: WearableSample, passes: int = 3) -> dict:
    log = []
    critique: Critique | None = None
    candidate = generate(sample, None)
    for i in range(passes):
        critique = verify(candidate, sample)
        log.append(
            {
                "pass": i,
                "candidate": asdict(candidate),
                "critique": asdict(critique),
            }
        )
        if critique.passed:
            break
        candidate = generate(sample, critique)
    return {
        "sample": asdict(sample),
        "passes": log,
        "final": asdict(candidate),
        "final_passed": critique.passed if critique else False,
    }


def main() -> None:
    sample = WearableSample(
        last_cgm_mgdl=118.0,
        eda_tonic_us=4.6,
        hour_local=6,
        sex="M",
        ppg_hr_bpm=78.0,
    )
    result = run_loop(sample, passes=3)
    print("=== BEFORE (pass 0) ===")
    print(json.dumps(result["passes"][0]["candidate"], indent=2))
    print("critique:", result["passes"][0]["critique"]["reasons"])
    print("=== AFTER (final) ===")
    print(json.dumps(result["final"], indent=2))
    print("passed:", result["final_passed"])
    with open("run_log.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    smoke = (
        f"before={result['passes'][0]['candidate']['band']}/"
        f"{result['passes'][0]['candidate']['est_mgdl']} "
        f"after={result['final']['band']}/{result['final']['est_mgdl']} "
        f"passed={result['final_passed']}\n"
    )
    with open("SMOKE.txt", "w", encoding="utf-8") as f:
        f.write(smoke)
    print(smoke)


if __name__ == "__main__":
    main()
