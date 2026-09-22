#!/usr/bin/env python3
"""GVU loop — 2026-09-23
Prevention / digital therapeutics slice:

Paper seed (Moschonis et al., eBioMedicine 2024): among diabetes self-management
apps, the BCT 'self-monitoring of behaviour' (β ≈ −0.22 HbA1c) and targeting
'taking medication' were the components associated with better glycaemic outcomes.

Generator drafts a 7-day digital-therapeutic plan from a short patient profile.
Verifier fails any plan that does not:
  1. name a measurable target behaviour with a numeric daily log
  2. include a medication-taking self-check if the profile is on meds
  3. include at least one concrete, time-bounded action (minutes or grams)
Updater feeds the critique back for up to 3 passes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import List


SAMPLE = {
    "id": "P-0923",
    "hba1c": 8.1,
    "on_medication": True,
    "meds": ["metformin 1000 mg BID"],
    "activity_min_week": 40,
    "logs_food": False,
    "logs_meds": False,
    "barrier": "forgets afternoon metformin; no written food record",
}


@dataclass
class Plan:
    headline: str
    target_behaviour: str
    daily_log: str
    medication_check: str
    concrete_actions: List[str]
    notes: str

    def as_text(self) -> str:
        actions = "; ".join(self.concrete_actions)
        return (
            f"HEADLINE: {self.headline}\n"
            f"TARGET: {self.target_behaviour}\n"
            f"DAILY_LOG: {self.daily_log}\n"
            f"MED_CHECK: {self.medication_check}\n"
            f"ACTIONS: {actions}\n"
            f"NOTES: {self.notes}"
        )


def generate(profile: dict, critique: str | None, pass_idx: int) -> Plan:
    if pass_idx == 0 and not critique:
        return Plan(
            headline="Try to eat better and walk more this week",
            target_behaviour="healthier lifestyle",
            daily_log="think about how the day went",
            medication_check="remember your tablets if you can",
            concrete_actions=["be more active", "cut sugar"],
            notes="generic first draft; no measurable self-monitor",
        )

    log = (
        "checkbox: metformin taken 08:00 and 20:00; write carb-grams at each meal; "
        "step-count at bedtime (target 8000)"
    )
    med = (
        f"two-tick self-check for {profile['meds'][0]} — miss = same-day catch-up rule + note why"
        if profile.get("on_medication")
        else "no scheduled meds"
    )
    actions = [
        "walk 30 minutes after the largest meal on 5 of 7 days",
        "cap dinner starch at 45 g carbohydrate, logged before eating",
        "bedtime review of the three checkboxes (meds / carbs / steps)",
    ]
    return Plan(
        headline="Self-monitor metformin + carbs + steps; close the afternoon-dose gap",
        target_behaviour="taking medication + carbohydrate logging",
        daily_log=log,
        medication_check=med,
        concrete_actions=actions,
        notes=f"revised after pass critique (len={len(critique or '')})",
    )


def verify(plan: Plan, profile: dict) -> dict:
    reasons: List[str] = []
    text = plan.as_text().lower()

    has_numeric_log = bool(re.search(r"\d+", plan.daily_log)) and (
        "log" in text or "checkbox" in text or "tick" in text or "write" in text
    )
    if not has_numeric_log:
        reasons.append(
            "FAIL self-monitor: daily_log must name a measurable behaviour with a numeric field"
        )

    if profile.get("on_medication"):
        med_ok = "metformin" in text or "medication" in text or "med" in text
        specific = "08:00" in plan.daily_log or "BID" in text or "tick" in text or "check" in text
        if not (med_ok and specific):
            reasons.append(
                "FAIL medication: on-meds profile requires an explicit timed self-check"
            )

    numeric_actions = [a for a in plan.concrete_actions if re.search(r"\d+", a)]
    if len(numeric_actions) < 1:
        reasons.append(
            "FAIL concrete action: need at least one time- or gram-bounded action"
        )

    vague = any(
        w in plan.target_behaviour.lower()
        for w in ("healthier", "lifestyle", "better", "wellness")
    )
    if vague:
        reasons.append("FAIL target: target_behaviour is too vague (not a BCT-grade behaviour)")

    passed = len(reasons) == 0
    return {
        "pass": passed,
        "reasons": reasons or ["all three success criteria met"],
        "criterion": (
            "Plan must (a) name a measurable target behaviour with a numeric daily log, "
            "(b) include a timed medication self-check when the profile is on meds, "
            "(c) include ≥1 concrete minutes-or-grams action. Grounded in Moschonis 2024 "
            "self-monitoring-of-behaviour + taking-medication BCTs."
        ),
    }


def run_gvu(profile: dict, max_passes: int = 3) -> dict:
    log = []
    critique = None
    plan = None
    verdict = None
    for i in range(max_passes):
        plan = generate(profile, critique, i)
        verdict = verify(plan, profile)
        log.append(
            {
                "pass": i,
                "plan": asdict(plan),
                "plan_text": plan.as_text(),
                "verdict": verdict,
            }
        )
        if verdict["pass"]:
            break
        critique = " | ".join(verdict["reasons"])
    return {
        "profile": profile,
        "passes": log,
        "final_pass": verdict["pass"] if verdict else False,
        "n_passes": len(log),
    }


def main() -> None:
    result = run_gvu(SAMPLE)
    print("=== BEFORE (pass 0) ===")
    print(result["passes"][0]["plan_text"])
    print("VERDICT:", result["passes"][0]["verdict"])
    print()
    print("=== AFTER (final pass) ===")
    print(result["passes"][-1]["plan_text"])
    print("VERDICT:", result["passes"][-1]["verdict"])
    print()
    print(f"final_pass={result['final_pass']} n_passes={result['n_passes']}")
    with open("run_log.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("wrote run_log.json")


if __name__ == "__main__":
    main()
