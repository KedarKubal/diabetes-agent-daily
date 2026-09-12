#!/usr/bin/env python3
"""
Day 2026-09-13 — Generator–Verifier–Updater prototype.

Opportunity: Prevention / digital therapeutics.
Underexploited insight from Graham et al., JAMA 2025 (AI-led DPP
noninferior to human coaching): treat the trial *composite endpoint*
as an explicit verifier, not a marketing slogan. A plan is only valid
if it can hit ≥1 of: 5% weight loss, 4% weight loss + 150 min/week PA,
or ≥0.2 pp A1c drop while A1c stays <6.5%.

Naive generator emits a vague "walk more" nudge. The verifier fails it
until the updater injects measurable minutes, energy deficit, and
self-monitoring — the three BCTs that actually drove the trial result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


SAMPLE = {
    "bmi": 31.2,
    "a1c": 6.1,
    "baseline_pa_min_week": 40,
    "prefers": "evenings",
}


@dataclass
class Plan:
    title: str
    weekly_pa_min: int
    calorie_deficit_kcal_day: int
    self_monitor: bool
    notes: str
    pass_n: int = 0

    def summary(self) -> str:
        return (
            f"{self.title} | PA={self.weekly_pa_min} min/wk | "
            f"deficit={self.calorie_deficit_kcal_day} kcal/d | "
            f"self_monitor={self.self_monitor} | {self.notes}"
        )


def generator(person: dict, critique: str | None, prior: Plan | None) -> Plan:
    if critique is None or prior is None:
        return Plan(
            title="Generic walk-more nudge",
            weekly_pa_min=person["baseline_pa_min_week"],
            calorie_deficit_kcal_day=0,
            self_monitor=False,
            notes="try to move a bit more this week",
        )

    pa = prior.weekly_pa_min
    deficit = prior.calorie_deficit_kcal_day
    monitor = prior.self_monitor
    notes = prior.notes

    if "minutes" in critique.lower() or "150" in critique:
        pa = max(pa, 150)
        notes = "3x50 min brisk walk evenings + 2x20 min resistance"
    if "deficit" in critique.lower() or "weight" in critique.lower():
        deficit = max(deficit, 500)
        notes += "; 500 kcal/d deficit via plate method"
    if "monitor" in critique.lower() or "self-monitor" in critique.lower():
        monitor = True
        notes += "; log weight 2x/wk + steps daily"

    return Plan(
        title="Composite-aligned DPP plan",
        weekly_pa_min=pa,
        calorie_deficit_kcal_day=deficit,
        self_monitor=monitor,
        notes=notes.strip("; "),
    )


def verifier(plan: Plan, person: dict) -> tuple[bool, str]:
    fails: List[str] = []
    if plan.weekly_pa_min < 150:
        fails.append(
            f"PA {plan.weekly_pa_min} < 150 min/week — raise minutes to hit composite"
        )
    if person["bmi"] >= 25 and plan.calorie_deficit_kcal_day < 400:
        fails.append(
            "BMI>=25 but deficit <400 kcal/d — add weight-loss deficit"
        )
    if not plan.self_monitor:
        fails.append("missing self-monitor — add daily steps + 2x/wk weight log")
    if plan.title.lower().startswith("generic"):
        fails.append("generic title — rewrite as composite-aligned DPP plan")

    if fails:
        return False, "; ".join(fails)
    return True, "PASS: 150+ min PA, energy deficit, self-monitoring, named plan"


def updater(person: dict, max_passes: int = 3) -> List[dict]:
    log = []
    critique = None
    plan = None
    for i in range(1, max_passes + 1):
        plan = generator(person, critique, plan)
        ok, reason = verifier(plan, person)
        plan.pass_n = i
        log.append(
            {
                "pass": i,
                "ok": ok,
                "reason": reason,
                "output": plan.summary(),
            }
        )
        if ok:
            break
        critique = reason
    return log


def main() -> None:
    print("SAMPLE PERSON:", SAMPLE)
    log = updater(SAMPLE)
    print("\n=== GVU PASSES ===")
    for row in log:
        flag = "PASS" if row["ok"] else "FAIL"
        print(f"\nPass {row['pass']} [{flag}]")
        print("  output :", row["output"])
        print("  reason :", row["reason"])
    print("\nBEFORE:", log[0]["output"])
    print("AFTER :", log[-1]["output"])


if __name__ == "__main__":
    main()
