#!/usr/bin/env python3
"""Day 2026-09-07 GVU: PPG + demographics prediabetes risk draft.

Generator: naive risk from last PPG amplitude only.
Verifier: explicit clinical-heuristic success criteria (falsifiable).
Updater: feeds critique back for 3 passes.

Success criterion (must ALL hold to PASS):
  1. risk_score is a float in [0.0, 1.0]
  2. label matches bins: high if score>=0.60, elevated if >=0.35, else low
  3. if age>=45 AND ac_dc_ratio<0.40, label cannot be 'low'
  4. explanation cites at least two of {age, ac_dc_ratio, pulse_arrival, hr_var}
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import List


FEATURES = ("age", "ac_dc_ratio", "pulse_arrival", "hr_var")


@dataclass
class Draft:
    risk_score: float
    label: str
    explanation: str
    used_features: List[str]


SAMPLE = {
    "age": 58,
    "ac_dc_ratio": 0.28,
    "pulse_arrival": 0.22,
    "hr_var": 0.08,
}


def generate(sample: dict, critique: str | None, pass_idx: int) -> Draft:
    """Pass 0 is naive (amplitude-only). Later passes incorporate critique."""
    ac = float(sample["ac_dc_ratio"])
    age = float(sample["age"])
    pav = float(sample["pulse_arrival"])
    hrv = float(sample["hr_var"])

    if pass_idx == 0 or not critique:
        score = max(0.0, min(1.0, 0.55 - ac))
        return Draft(
            risk_score=round(score, 3),
            label="low",
            explanation="Looks fine from pulse strength alone.",
            used_features=["ac_dc_ratio"],
        )

    score = 0.15
    if age >= 45:
        score += 0.22
    if ac < 0.40:
        score += 0.28
    if pav > 0.18:
        score += 0.12
    if hrv < 0.12:
        score += 0.15
    score = max(0.0, min(1.0, score))
    if score >= 0.60:
        label = "high"
    elif score >= 0.35:
        label = "elevated"
    else:
        label = "low"
    return Draft(
        risk_score=round(score, 3),
        label=label,
        explanation=(
            f"Age {age:.0f} and low ac_dc_ratio {ac:.2f} raise prediabetes risk; "
            f"pulse_arrival {pav:.2f}s and hr_var {hrv:.2f} corroborate."
        ),
        used_features=list(FEATURES),
    )


def verify(draft: Draft, sample: dict) -> tuple[bool, str]:
    reasons = []
    score = draft.risk_score
    if not (0.0 <= score <= 1.0):
        reasons.append(f"score {score} not in [0,1]")

    expected = "high" if score >= 0.60 else "elevated" if score >= 0.35 else "low"
    if draft.label != expected:
        reasons.append(f"label '{draft.label}' != bin '{expected}' for score {score}")

    if sample["age"] >= 45 and sample["ac_dc_ratio"] < 0.40 and draft.label == "low":
        reasons.append("age>=45 and ac_dc_ratio<0.40 cannot be labeled low")

    cited = set(draft.used_features) | {
        f for f in FEATURES if f in draft.explanation.lower() or f.replace("_", " ") in draft.explanation.lower()
    }
    if len(cited & set(FEATURES)) < 2:
        reasons.append("explanation must cite at least two of age, ac_dc_ratio, pulse_arrival, hr_var")

    if reasons:
        return False, "; ".join(reasons)
    return True, "all four success criteria met"


def run(sample: dict, max_passes: int = 3) -> list[dict]:
    log = []
    critique = None
    for i in range(max_passes):
        draft = generate(sample, critique, i)
        ok, reason = verify(draft, sample)
        row = {"pass": i, "ok": ok, "reason": reason, "draft": asdict(draft)}
        log.append(row)
        print(f"PASS {i}: {'PASS' if ok else 'FAIL'} | {reason}")
        print(f"  draft: {json.dumps(asdict(draft))}")
        if ok:
            break
        critique = reason
    return log


if __name__ == "__main__":
    print("Sample:", SAMPLE)
    history = run(SAMPLE)
    print("\nBEFORE (pass 0):", json.dumps(history[0]["draft"]))
    print("AFTER  (last):  ", json.dumps(history[-1]["draft"]))
    with open("run_log.json", "w") as f:
        json.dump({"sample": SAMPLE, "history": history}, f, indent=2)
    print("Wrote run_log.json")
