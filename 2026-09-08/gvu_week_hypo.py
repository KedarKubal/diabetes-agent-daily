#!/usr/bin/env python3
"""
Day 2026-09-08 — Week-ahead hypoglycemia risk GVU loop.

Insight (Cichosz 2024 / Giammarino 2024): last week's LBGI, TBR, CV, and
mean glucose predict next-week excessive hypoglycemia better than last-point
snapshots. Generator starts naive (mean-only); Verifier requires the
discriminative weekly features; Updater revises 2–3 passes.

Success criterion (falsifiable):
  PASS iff
    1) risk_label in {low, moderate, high}
    2) high if TBR>4% OR LBGI>=2.5 OR (CV>=0.36 and mean<140)
       moderate if TBR>=2% or LBGI>=1.1 else low
    3) cited_features includes at least {tbr_pct, lbgi, cv}
    4) rationale mentions next-week (not only current reading)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import List


@dataclass
class WeekCGM:
    readings_mgdl: List[float]

    @property
    def mean(self) -> float:
        return sum(self.readings_mgdl) / len(self.readings_mgdl)

    @property
    def std(self) -> float:
        m = self.mean
        var = sum((x - m) ** 2 for x in self.readings_mgdl) / len(self.readings_mgdl)
        return math.sqrt(var)

    @property
    def cv(self) -> float:
        return self.std / self.mean if self.mean else 0.0

    @property
    def tbr_pct(self) -> float:
        below = sum(1 for x in self.readings_mgdl if x < 70)
        return 100.0 * below / len(self.readings_mgdl)

    @property
    def lbgi(self) -> float:
        def f(g: float) -> float:
            g = max(g, 20.0)
            return 1.509 * ((math.log(g) ** 1.084) - 5.381)

        risks = []
        for g in self.readings_mgdl:
            rl = 10 * (f(g) ** 2)
            if f(g) < 0:
                risks.append(rl)
            else:
                risks.append(0.0)
        return sum(risks) / len(risks)


def expected_label(week: WeekCGM) -> str:
    if week.tbr_pct > 4.0 or week.lbgi >= 2.5 or (week.cv >= 0.36 and week.mean < 140):
        return "high"
    if week.tbr_pct >= 2.0 or week.lbgi >= 1.1:
        return "moderate"
    return "low"


def generator(week: WeekCGM, critique: str | None, prior: dict | None) -> dict:
    if critique is None:
        last = week.readings_mgdl[-1]
        if last < 70:
            label = "high"
        elif last < 90:
            label = "moderate"
        else:
            label = "low"
        return {
            "risk_label": label,
            "risk_score": round(max(0.0, (90 - last) / 90), 3),
            "cited_features": ["last_reading", "mean"],
            "values": {"last": last, "mean": round(week.mean, 1)},
            "rationale": f"Last CGM point is {last:.0f} mg/dL; mean this week {week.mean:.0f}.",
        }

    label = expected_label(week)
    score = min(1.0, (week.tbr_pct / 8.0) + (week.lbgi / 5.0) + max(0.0, week.cv - 0.30))
    return {
        "risk_label": label,
        "risk_score": round(score, 3),
        "cited_features": ["tbr_pct", "lbgi", "cv", "mean"],
        "values": {
            "tbr_pct": round(week.tbr_pct, 2),
            "lbgi": round(week.lbgi, 3),
            "cv": round(week.cv, 3),
            "mean": round(week.mean, 1),
        },
        "rationale": (
            f"Next-week excessive-hypoglycemia risk is {label} because last-week "
            f"TBR={week.tbr_pct:.1f}% (ADA target <4%), LBGI={week.lbgi:.2f}, "
            f"CV={week.cv:.2f}, mean={week.mean:.0f} mg/dL."
        ),
    }


def verifier(week: WeekCGM, draft: dict) -> dict:
    want = expected_label(week)
    reasons = []
    ok = True

    if draft.get("risk_label") not in {"low", "moderate", "high"}:
        ok = False
        reasons.append("label not in {low, moderate, high}")

    if draft.get("risk_label") != want:
        ok = False
        reasons.append(
            f"label {draft.get('risk_label')} != expected {want} from TBR/LBGI/CV rule"
        )

    needed = {"tbr_pct", "lbgi", "cv"}
    cited = set(draft.get("cited_features") or [])
    if not needed.issubset(cited):
        ok = False
        reasons.append(f"missing weekly features {sorted(needed - cited)}")

    rationale = (draft.get("rationale") or "").lower()
    if "next-week" not in rationale and "next week" not in rationale:
        ok = False
        reasons.append("rationale must frame risk as next-week, not only current reading")

    return {
        "pass": ok,
        "expected_label": want,
        "reason": "OK" if ok else "; ".join(reasons),
    }


def gvu_loop(week: WeekCGM, max_passes: int = 3) -> list:
    log = []
    critique = None
    draft = None
    for i in range(1, max_passes + 1):
        draft = generator(week, critique, draft)
        check = verifier(week, draft)
        log.append({"pass": i, "draft": draft, "verifier": check})
        if check["pass"]:
            break
        critique = check["reason"]
    return log


def sample_week() -> WeekCGM:
    vals = [118, 142, 95, 64, 58, 81, 156, 171, 88, 61, 73, 190, 102, 55, 134]
    return WeekCGM(vals)


def main() -> None:
    week = sample_week()
    feats = {
        "mean": round(week.mean, 1),
        "cv": round(week.cv, 3),
        "tbr_pct": round(week.tbr_pct, 2),
        "lbgi": round(week.lbgi, 3),
        "last": week.readings_mgdl[-1],
        "expected": expected_label(week),
    }
    print("SAMPLE WEEK FEATURES", json.dumps(feats))
    log = gvu_loop(week)
    print("\n=== BEFORE / AFTER ===")
    print("PASS 1 (before):", json.dumps(log[0]["draft"], indent=2))
    print("VERIFIER 1:", log[0]["verifier"])
    print("\nFINAL (after):", json.dumps(log[-1]["draft"], indent=2))
    print("VERIFIER FINAL:", log[-1]["verifier"])
    print(f"\npasses_run={len(log)} final_pass={log[-1]['verifier']['pass']}")


if __name__ == "__main__":
    main()
