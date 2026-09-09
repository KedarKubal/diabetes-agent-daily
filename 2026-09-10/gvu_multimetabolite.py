#!/usr/bin/env python3
"""
Day 2026-09-10 — Generator–Verifier–Updater
Opportunity: fingertip sweat microgrid multi-metabolite consistency
(Ding et al., Nature Electronics 2024).

Generator drafts a glucose-risk flag from a fingertip panel
(glucose, lactate, vitamin C, levodopa-proxy).
Verifier requires the flag to be consistent with the rest of the panel
(not glucose-in-isolation).
Updater revises 3 times.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Panel:
    sweat_glucose_uM: float
    lactate_mM: float
    vitamin_c_uM: float
    activity_proxy: str  # "rest" | "exercise" | "postprandial"
    age: int


@dataclass
class Draft:
    risk: str  # LOW | MODERATE | HIGH
    score: float  # 0-1
    rationale: str


def generate(panel: Panel, critique: str | None = None) -> Draft:
    """Naive first pass uses glucose only; later passes fold in critique."""
    g = panel.sweat_glucose_uM
    if critique is None:
        if g >= 200:
            return Draft("HIGH", 0.82, "sweat glucose alone above 200 uM")
        if g >= 100:
            return Draft("MODERATE", 0.55, "sweat glucose alone mid-range")
        return Draft("LOW", 0.22, "sweat glucose alone low")

    score = min(0.95, g / 280.0)
    notes = []
    if panel.activity_proxy == "exercise" and panel.lactate_mM >= 4.0:
        score *= 0.7
        notes.append("exercise + high lactate: glucose rise is expected, downweight")
    if panel.activity_proxy == "rest" and panel.lactate_mM < 2.0 and g >= 180:
        score = min(0.95, score + 0.18)
        notes.append("resting + low lactate + high glucose: upweight metabolic risk")
    if panel.vitamin_c_uM < 20:
        score = min(0.95, score + 0.05)
        notes.append("low vitamin C: oxidative-stress co-signal")
    if panel.age >= 50:
        score = min(0.95, score + 0.05)
        notes.append("age >= 50")

    if score >= 0.65:
        risk = "HIGH"
    elif score >= 0.40:
        risk = "MODERATE"
    else:
        risk = "LOW"
    rationale = "; ".join(notes) if notes else "panel-adjusted glucose score"
    return Draft(risk, round(score, 3), rationale)


def verify(panel: Panel, draft: Draft) -> tuple[bool, str]:
    """
    Success criterion (falsifiable):
    1. Risk label must match score bands: HIGH>=0.65, MODERATE>=0.40, else LOW.
    2. Must not emit HIGH on exercise+high-lactate without downweight note.
    3. Must not emit LOW on rest+low-lactate+glucose>=180.
    4. Rationale must cite at least one non-glucose analyte or context tag.
    """
    fails = []
    if draft.risk == "HIGH" and draft.score < 0.65:
        fails.append("HIGH label with score < 0.65")
    if draft.risk == "MODERATE" and not (0.40 <= draft.score < 0.65):
        fails.append("MODERATE label outside [0.40, 0.65)")
    if draft.risk == "LOW" and draft.score >= 0.40:
        fails.append("LOW label with score >= 0.40")

    if (
        panel.activity_proxy == "exercise"
        and panel.lactate_mM >= 4.0
        and draft.risk == "HIGH"
        and "lactate" not in draft.rationale.lower()
    ):
        fails.append("HIGH during exercise/high-lactate without lactate context")

    if (
        panel.activity_proxy == "rest"
        and panel.lactate_mM < 2.0
        and panel.sweat_glucose_uM >= 180
        and draft.risk == "LOW"
    ):
        fails.append("LOW despite rest + low lactate + high sweat glucose")

    non_glu = any(
        k in draft.rationale.lower()
        for k in ("lactate", "vitamin", "exercise", "rest", "age", "panel")
    )
    if not non_glu:
        fails.append("rationale cites glucose only; need multi-metabolite context")

    if fails:
        return False, "; ".join(fails)
    return True, "panel-consistent risk label"


def run_gvu(panel: Panel, max_passes: int = 3) -> dict:
    log = []
    critique = None
    draft = None
    passed = False
    reason = ""
    for i in range(1, max_passes + 1):
        draft = generate(panel, critique)
        passed, reason = verify(panel, draft)
        log.append(
            {
                "pass": i,
                "draft": asdict(draft),
                "passed": passed,
                "reason": reason,
            }
        )
        if passed:
            break
        critique = reason
    return {
        "panel": asdict(panel),
        "final": asdict(draft) if draft else None,
        "passed": passed,
        "passes": log,
    }


if __name__ == "__main__":
    sample = Panel(
        sweat_glucose_uM=210,
        lactate_mM=1.1,
        vitamin_c_uM=12,
        activity_proxy="rest",
        age=58,
    )
    result = run_gvu(sample)
    print(json.dumps(result, indent=2))
