#!/usr/bin/env python3
"""
Day 2026-09-27 — GVU prototype
Opportunity: Monitoring — statistically guided SOFT labels near the 70 mg/dL
hypoglycemia boundary (inspired by MT-HypoNet, iScience 2026).

Generator: naive last-point binary flag.
Verifier: explicit soft-score + citation rules (falsifiable).
Updater: feeds critique back for up to 3 passes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List


HYPO_LINE = 70.0
NEAR_LO, NEAR_HI = 65.0, 75.0
FAR_LOW = 65.0
FAR_HIGH = 80.0


@dataclass
class Draft:
    risk: str  # HIGH | MEDIUM | LOW
    soft_score: float  # 0..1 probability-like
    cites: List[str]
    note: str
    pass_idx: int = 0


@dataclass
class Critique:
    passed: bool
    reasons: List[str] = field(default_factory=list)


def features(window: List[float]) -> dict:
    last = float(window[-1])
    slope = float(window[-1] - window[0]) / max(len(window) - 1, 1)
    n_below = sum(1 for g in window if g < HYPO_LINE)
    return {"last": last, "slope": slope, "n_below": n_below, "n": len(window)}


def generate(window: List[float], critique: Critique | None, pass_idx: int) -> Draft:
    """Pass 0: last-point binary. Later passes apply verifier rules."""
    f = features(window)
    last, slope = f["last"], f["slope"]

    if critique is None or pass_idx == 0:
        if last < HYPO_LINE:
            return Draft("HIGH", 1.0, ["last_glucose"], f"last={last:.1f}<70 hard HIGH", 0)
        return Draft("LOW", 0.0, ["last_glucose"], f"last={last:.1f}>=70 hard LOW", 0)

    if last < FAR_LOW:
        score = min(0.95, 0.80 + 0.02 * (FAR_LOW - last) + max(0.0, -slope) * 0.01)
        risk = "HIGH"
    elif last > FAR_HIGH:
        score = max(0.05, 0.15 - 0.01 * (last - FAR_HIGH) + max(0.0, -slope) * 0.02)
        risk = "LOW" if score < 0.25 else "MEDIUM"
    else:
        t = (last - NEAR_LO) / (NEAR_HI - NEAR_LO)
        score = 0.62 - 0.24 * t
        if slope < -2:
            score = min(0.65, score + 0.08)
        risk = "MEDIUM"

    cites = ["last_glucose", "slope"]
    if f["n_below"] >= 2:
        cites.append("n_below")
    return Draft(
        risk,
        round(score, 3),
        cites,
        f"soft last={last:.1f} slope={slope:.2f} n_below={f['n_below']}",
        pass_idx,
    )


def verify(draft: Draft, window: List[float]) -> Critique:
    f = features(window)
    last = f["last"]
    reasons: List[str] = []

    if not (0.0 <= draft.soft_score <= 1.0):
        reasons.append(f"score {draft.soft_score} outside [0,1]")

    if last < FAR_LOW:
        if draft.soft_score < 0.80:
            reasons.append(f"far-low last={last:.1f} needs score>=0.80 got {draft.soft_score}")
        if draft.risk != "HIGH":
            reasons.append(f"far-low needs HIGH got {draft.risk}")
    elif last > FAR_HIGH:
        if draft.soft_score > 0.20:
            reasons.append(f"far-high last={last:.1f} needs score<=0.20 got {draft.soft_score}")
        if draft.risk != "LOW":
            reasons.append(f"far-high needs LOW got {draft.risk}")
    elif NEAR_LO <= last <= NEAR_HI:
        if not (0.35 <= draft.soft_score <= 0.65):
            reasons.append(
                f"boundary last={last:.1f} needs score in [0.35,0.65] got {draft.soft_score}"
            )
        if draft.risk != "MEDIUM":
            reasons.append(f"boundary needs MEDIUM got {draft.risk}")

    if "last_glucose" not in draft.cites:
        reasons.append("missing cite last_glucose")
    if "slope" not in draft.cites:
        reasons.append("missing cite slope")

    return Critique(passed=len(reasons) == 0, reasons=reasons)


def run_gvu(window: List[float], max_passes: int = 3) -> list[dict]:
    log = []
    critique: Critique | None = None
    draft = generate(window, None, 0)
    for i in range(max_passes):
        critique = verify(draft, window)
        log.append(
            {
                "pass": i,
                "draft": asdict(draft),
                "passed": critique.passed,
                "reasons": critique.reasons,
            }
        )
        if critique.passed:
            break
        draft = generate(window, critique, i + 1)
    return log


def main() -> None:
    sample = [88.0, 84.0, 79.0, 75.0, 72.0]
    log = run_gvu(sample)
    out_dir = Path(__file__).resolve().parent
    (out_dir / "run_log.json").write_text(json.dumps(log, indent=2))
    before = log[0]["draft"]
    after = log[-1]["draft"]
    smoke = (
        f"BEFORE pass0: risk={before['risk']} score={before['soft_score']} cites={before['cites']}\n"
        f"AFTER  pass{log[-1]['pass']}: risk={after['risk']} score={after['soft_score']} cites={after['cites']}\n"
        f"verifier_passed={log[-1]['passed']} reasons={log[-1]['reasons']}\n"
    )
    (out_dir / "SMOKE.txt").write_text(smoke)
    print(smoke)


if __name__ == "__main__":
    main()
