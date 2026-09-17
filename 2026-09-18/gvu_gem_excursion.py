#!/usr/bin/env python3
"""Day 2026-09-18 — GVU agent: post-meal glycemic-excursion risk + next-meal nudge.

Insight prototyped (Cox GEM + CGM): minimize *excursions* (peak and rise),
not only fasting/A1c or last-point glucose. A last-reading-only draft is
wrong when pre-meal slope + carb load predict a peak >180 or rise >50.

Verifier success criterion (falsifiable):
  PASS iff predicted_peak_mgdl <= 180
       AND predicted_rise_mgdl <= 50
       AND cited_features includes at least two of
           {pre_meal_glucose, slope_15min, carb_g}
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List


# --- sample "patient" window (pre-meal CGM + planned meal) ---
SAMPLE = {
    "pre_meal_glucose": 142,  # mg/dL
    "glucose_15min_ago": 128,
    "carb_g": 65,  # planned next meal
    "activity_after_meal_min": 0,
}


@dataclass
class Draft:
    predicted_peak_mgdl: float
    predicted_rise_mgdl: float
    risk: str
    nudge: str
    cited_features: List[str] = field(default_factory=list)
    notes: str = ""


def _slope(sample: dict) -> float:
    return float(sample["pre_meal_glucose"] - sample["glucose_15min_ago"])


def generator(sample: dict, critique: str | None = None) -> Draft:
    """Pass 0 ignores slope/carbs (last-point vibe). Later passes apply GEM physics."""
    pre = float(sample["pre_meal_glucose"])
    sl = _slope(sample)
    carbs = float(sample["carb_g"])
    walk = float(sample["activity_after_meal_min"])

    if critique is None:
        return Draft(
            predicted_peak_mgdl=pre,
            predicted_rise_mgdl=0.0,
            risk="LOW",
            nudge="Current glucose looks fine. Eat as planned.",
            cited_features=["pre_meal_glucose"],
            notes="pass-0 last-point only",
        )

    rise = 1.8 * carbs + 2.0 * sl - 0.6 * walk
    peak = pre + max(rise, 0.0)

    if peak > 180 or rise > 50:
        carbs_adj, walk_adj = carbs, walk
        for c_frac, w_min in ((0.45, 15), (0.35, 20), (0.25, 25), (0.20, 30)):
            carbs_adj = max(15.0, carbs * c_frac)
            walk_adj = max(walk, float(w_min))
            rise = 1.8 * carbs_adj + 2.0 * sl - 0.6 * walk_adj
            peak = pre + max(rise, 0.0)
            if peak <= 180 and rise <= 50:
                break
        nudge = (
            f"GEM nudge: cap this meal at ~{int(carbs_adj)} g digestible carb "
            f"(swap the rest for protein/veg) and walk {int(walk_adj)} min after eating."
        )
        risk = "HIGH_THEN_MITIGATED" if peak <= 180 and rise <= 50 else "HIGH"
    else:
        nudge = "Meal size is compatible with a <180 peak. Keep protein-first order."
        risk = "MODERATE" if rise > 30 else "LOW"

    return Draft(
        predicted_peak_mgdl=round(peak, 1),
        predicted_rise_mgdl=round(rise, 1),
        risk=risk,
        nudge=nudge,
        cited_features=["pre_meal_glucose", "slope_15min", "carb_g"],
        notes="pass-revised GEM excursion model",
    )


def verifier(draft: Draft) -> tuple[bool, str]:
    needed = {"pre_meal_glucose", "slope_15min", "carb_g"}
    cited = set(draft.cited_features)
    missing = needed - cited
    peak_ok = draft.predicted_peak_mgdl <= 180
    rise_ok = draft.predicted_rise_mgdl <= 50
    cite_ok = len(needed & cited) >= 2
    ok = peak_ok and rise_ok and cite_ok
    reason = (
        f"peak={draft.predicted_peak_mgdl} (<=180? {peak_ok}); "
        f"rise={draft.predicted_rise_mgdl} (<=50? {rise_ok}); "
        f"cited={sorted(cited)} missing={sorted(missing)} cite_ok={cite_ok}"
    )
    return ok, reason


def updater(sample: dict, max_passes: int = 3) -> list[dict]:
    log: list[dict] = []
    critique: str | None = None
    draft = generator(sample, critique)
    for i in range(max_passes):
        passed, reason = verifier(draft)
        log.append(
            {
                "pass": i,
                "passed": passed,
                "reason": reason,
                "draft": asdict(draft),
            }
        )
        if passed:
            break
        critique = reason
        draft = generator(sample, critique)
    return log


def main() -> None:
    log = updater(SAMPLE, max_passes=3)
    out_dir = Path(__file__).resolve().parent
    (out_dir / "run_log.json").write_text(json.dumps(log, indent=2))
    print("=== SAMPLE INPUT ===")
    print(json.dumps(SAMPLE, indent=2))
    print("\n=== GVU PASSES ===")
    for row in log:
        d = row["draft"]
        print(
            f"pass {row['pass']}: passed={row['passed']} "
            f"peak={d['predicted_peak_mgdl']} rise={d['predicted_rise_mgdl']} "
            f"risk={d['risk']}"
        )
        print(f"  nudge: {d['nudge']}")
        print(f"  verify: {row['reason']}")
    first, last = log[0]["draft"], log[-1]["draft"]
    print("\n=== BEFORE / AFTER ===")
    print(f"before: peak={first['predicted_peak_mgdl']} risk={first['risk']} | {first['nudge']}")
    print(f"after:  peak={last['predicted_peak_mgdl']} risk={last['risk']} | {last['nudge']}")


if __name__ == "__main__":
    main()
