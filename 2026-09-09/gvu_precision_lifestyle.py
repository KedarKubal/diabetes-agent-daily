#!/usr/bin/env python3
"""
Day 2026-09-09 — Generator–Verifier–Updater prototype.

Opportunity: Prevention / digital therapeutics — subgroup-aware lifestyle
nudge (inspired by Otten et al. 2023 npj Digital Medicine: digital lifestyle
treatment has larger HbA1c effect in high-BMI / insulin-resistant subgroups
and FTO non-risk carriers).

Generator: drafts a 7-day glycemic lifestyle plan from a tiny patient card.
Verifier: explicit, falsifiable rules (not vibes).
Updater: feeds critique back; 3 passes max.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import List


SAMPLE = {
    "bmi": 33.4,
    "homa_ir": 3.8,
    "fto_risk_allele": False,
    "baseline_hba1c": 7.6,
    "steps_per_day": 3200,
    "evening_snacks": True,
}


@dataclass
class Plan:
    intensity: str
    weekly_mvpa_min: int
    resistance_sessions: int
    calorie_deficit_kcal: int
    snack_rule: str
    cited_features: List[str]
    rationale: str

    def to_dict(self):
        return asdict(self)


def generate(patient: dict, critique: str | None = None) -> Plan:
    if critique is None:
        return Plan(
            intensity="low",
            weekly_mvpa_min=90,
            resistance_sessions=0,
            calorie_deficit_kcal=0,
            snack_rule="no change",
            cited_features=["baseline_hba1c"],
            rationale="Generic walk-more plan; ignores BMI/IR/FTO.",
        )

    high_ir = patient["homa_ir"] >= 2.9
    high_bmi = patient["bmi"] >= 30
    nonrisk_fto = not patient["fto_risk_allele"]
    cited = []
    if high_bmi:
        cited.append("bmi")
    if high_ir:
        cited.append("homa_ir")
    if nonrisk_fto:
        cited.append("fto_non_risk")
    if patient["evening_snacks"]:
        cited.append("evening_snacks")
    if patient["steps_per_day"] < 5000:
        cited.append("steps_per_day")

    if high_bmi and high_ir:
        intensity = "high"
        mvpa = 180
        resist = 3
        deficit = 500
    elif high_bmi or high_ir:
        intensity = "moderate"
        mvpa = 150
        resist = 2
        deficit = 300
    else:
        intensity = "low"
        mvpa = 120
        resist = 1
        deficit = 0

    snack = (
        "no evening energy-dense snacks after 20:00"
        if patient["evening_snacks"]
        else "keep current snack window"
    )
    return Plan(
        intensity=intensity,
        weekly_mvpa_min=mvpa,
        resistance_sessions=resist,
        calorie_deficit_kcal=deficit,
        snack_rule=snack,
        cited_features=cited,
        rationale="Escalated from critique using BMI/IR/FTO subgroup rule.",
    )


def verify(plan: Plan, patient: dict) -> tuple[bool, str]:
    reasons = []
    high_ir = patient["homa_ir"] >= 2.9
    high_bmi = patient["bmi"] >= 30
    if high_bmi and high_ir:
        if plan.intensity != "high":
            reasons.append("high BMI+IR requires intensity=high")
        if plan.resistance_sessions < 2:
            reasons.append("high BMI+IR requires >=2 resistance sessions")
        if plan.calorie_deficit_kcal < 400:
            reasons.append("high BMI+IR requires deficit >=400 kcal")
    allowed = {"bmi", "homa_ir", "fto_non_risk", "steps_per_day", "evening_snacks"}
    n_cite = len(set(plan.cited_features) & allowed)
    if n_cite < 2:
        reasons.append(f"must cite >=2 subgroup features, got {n_cite}")
    if patient["evening_snacks"] and plan.snack_rule.strip().lower() == "no change":
        reasons.append("evening_snacks=True but snack_rule is 'no change'")
    if reasons:
        return False, "; ".join(reasons)
    return True, "pass: subgroup intensity + >=2 feature citations + snack rule"


def run_gvu(patient: dict, max_passes: int = 3) -> list[dict]:
    log = []
    critique = None
    for i in range(1, max_passes + 1):
        plan = generate(patient, critique)
        ok, reason = verify(plan, patient)
        log.append({"pass": i, "ok": ok, "reason": reason, "plan": plan.to_dict()})
        if ok:
            break
        critique = reason
    return log


def main():
    log = run_gvu(SAMPLE)
    print(json.dumps({"patient": SAMPLE, "passes": log}, indent=2))
    with open("run_log.json", "w") as f:
        json.dump({"patient": SAMPLE, "passes": log}, f, indent=2)


if __name__ == "__main__":
    main()
