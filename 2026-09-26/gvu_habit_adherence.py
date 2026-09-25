#!/usr/bin/env python3
"""Day 2026-09-26 GVU: habit-countable T2D prevention plan.

Insight (Stop Diabetes pragmatic RCT, Lakka et al. 2023 / Lancet Reg Health):
good adherence (>=median 501 habits/year digital, or >=5 of 6 group sessions)
is what moved diet quality and insulin resistance — not app presence.

Generator starts with a vague lifestyle draft.
Verifier fails unless the plan has:
  - at least 3 named habits
  - each habit has cue + weekly frequency
  - weekly_habit_quota >= 10 (proxy for the paper's high-adherence tail)
Updater rewrites until the criterion holds (max 3 passes).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Habit:
    name: str
    cue: str
    weekly_freq: int
    reward: str = ""


@dataclass
class Plan:
    summary: str
    habits: list[Habit] = field(default_factory=list)
    weekly_habit_quota: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "habits": [asdict(h) for h in self.habits],
            "weekly_habit_quota": self.weekly_habit_quota,
            "notes": self.notes,
        }


def generate(sample: dict, critique: str | None = None) -> Plan:
    """Naive first pass is a generic slogan; later passes incorporate critique."""
    if not critique:
        return Plan(
            summary="Walk more and eat healthier this week.",
            habits=[],
            weekly_habit_quota=0,
            notes=["first draft: last-point / slogan style"],
        )

    habits = [
        Habit(
            name="post_meal_walk",
            cue="immediately after lunch and dinner",
            weekly_freq=12,
            reward="tick habit counter + 10 min TIR log",
        ),
        Habit(
            name="veg_first_plate",
            cue="sit down to any meal",
            weekly_freq=14,
            reward="habit tick before first bite",
        ),
        Habit(
            name="evening_group_or_app_session",
            cue="20:00 phone alarm on Mon/Wed",
            weekly_freq=2,
            reward="session logged toward 5-of-6 quota",
        ),
        Habit(
            name="waist_self_measure",
            cue="Sunday morning after shower",
            weekly_freq=1,
            reward="cm recorded in app",
        ),
    ]
    quota = sum(h.weekly_freq for h in habits)
    return Plan(
        summary=(
            "High-adherence digital+group week: cue-bound habits totaling "
            f"{quota} ticks (Stop-Diabetes adherence lever)."
        ),
        habits=habits,
        weekly_habit_quota=quota,
        notes=["revised after verifier: countable habits + quota"],
    )


def verify(plan: Plan) -> tuple[bool, str]:
    named = [h for h in plan.habits if h.name.strip()]
    with_cue_freq = [h for h in named if h.cue.strip() and h.weekly_freq >= 1]
    quota = plan.weekly_habit_quota or sum(h.weekly_freq for h in with_cue_freq)

    fails: list[str] = []
    if len(named) < 3:
        fails.append(f"need >=3 named habits, got {len(named)}")
    if len(with_cue_freq) < 3:
        fails.append(f"need >=3 habits with cue+frequency, got {len(with_cue_freq)}")
    if quota < 10:
        fails.append(f"weekly_habit_quota must be >=10, got {quota}")
    if fails:
        return False, "; ".join(fails)
    return True, f"pass: {len(with_cue_freq)} cue-bound habits, quota={quota}"


def run_gvu(sample: dict, max_passes: int = 3) -> list[dict]:
    log: list[dict] = []
    critique: str | None = None
    plan = Plan(summary="")
    for i in range(1, max_passes + 1):
        plan = generate(sample, critique)
        ok, reason = verify(plan)
        entry = {
            "pass": i,
            "ok": ok,
            "reason": reason,
            "plan": plan.to_dict(),
        }
        log.append(entry)
        if ok:
            break
        critique = reason
    return log


SAMPLE = {
    "user": "prediabetes_adult",
    "baseline_waist_cm": 98,
    "homa_ir_trend": "rising",
}


def main() -> None:
    log = run_gvu(SAMPLE)
    out_dir = Path(__file__).resolve().parent
    (out_dir / "run_log.json").write_text(json.dumps(log, indent=2))
    first = log[0]
    last = log[-1]
    smoke = [
        "SMOKE 2026-09-26 habit-adherence GVU",
        f"before: summary={first['plan']['summary']!r} ok={first['ok']} ({first['reason']})",
        f"after:  summary={last['plan']['summary']!r} ok={last['ok']} ({last['reason']})",
        f"passes={len(log)} quota={last['plan']['weekly_habit_quota']}",
    ]
    text = "\n".join(smoke) + "\n"
    (out_dir / "SMOKE.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
