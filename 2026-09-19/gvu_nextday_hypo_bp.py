#!/usr/bin/env python3
"""GVU: next-day hypoglycemia risk from 10-day BG + BP sequences.

Paper insight (IEEE Access 2024): next-day hypo in T2D is predictable from
10-day temporal sequences of capillary BG *and* blood pressure — last-point
glucose is not enough.

Verifier success criterion (falsifiable):
  PASS iff ALL of:
    1. risk in {LOW, MEDIUM, HIGH}
    2. cited_features includes at least one BG-window feature AND one BP feature
    3. if any of last 3 days has bg_min < 70 OR (delta_mean_bg < -15 and
       delta_sbp > +5): risk must be HIGH
    4. nudge does not mention insulin dose / units / bolus
    5. nudge length 40–280 chars
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SAMPLE = {
    "days": [
        {"bg_mean": 142, "bg_min": 88, "sbp": 118, "dbp": 74},
        {"bg_mean": 138, "bg_min": 82, "sbp": 120, "dbp": 76},
        {"bg_mean": 135, "bg_min": 79, "sbp": 122, "dbp": 76},
        {"bg_mean": 129, "bg_min": 74, "sbp": 124, "dbp": 78},
        {"bg_mean": 126, "bg_min": 71, "sbp": 126, "dbp": 78},
        {"bg_mean": 121, "bg_min": 68, "sbp": 128, "dbp": 80},
        {"bg_mean": 118, "bg_min": 64, "sbp": 130, "dbp": 82},
        {"bg_mean": 116, "bg_min": 61, "sbp": 132, "dbp": 82},
        {"bg_mean": 114, "bg_min": 58, "sbp": 134, "dbp": 84},
        {"bg_mean": 118, "bg_min": 72, "sbp": 136, "dbp": 84},
    ]
}


@dataclass
class Draft:
    risk: str
    cited_features: list[str]
    nudge: str
    notes: str


def _features(days: list[dict]) -> dict[str, float]:
    last3 = days[-3:]
    first3 = days[:3]
    hypo_days = sum(1 for d in days if d["bg_min"] < 70)
    hypo_last3 = sum(1 for d in last3 if d["bg_min"] < 70)
    mean_bg_early = sum(d["bg_mean"] for d in first3) / 3
    mean_bg_late = sum(d["bg_mean"] for d in last3) / 3
    sbp_early = sum(d["sbp"] for d in first3) / 3
    sbp_late = sum(d["sbp"] for d in last3) / 3
    return {
        "last_bg_mean": days[-1]["bg_mean"],
        "hypo_days_10": hypo_days,
        "hypo_last3": hypo_last3,
        "delta_mean_bg": mean_bg_late - mean_bg_early,
        "delta_sbp": sbp_late - sbp_early,
        "last_sbp": days[-1]["sbp"],
    }


def generator(days: list[dict], critique: str | None = None) -> Draft:
    f = _features(days)
    if critique is None:
        return Draft(
            risk="LOW",
            cited_features=["last_bg_mean"],
            nudge="Last reading 118 looks fine. Keep usual routine.",
            notes="pass0 last-point only",
        )

    risk = "LOW"
    cited = ["last_bg_mean"]
    if f["hypo_last3"] >= 1 or (f["delta_mean_bg"] < -15 and f["delta_sbp"] > 5):
        risk = "HIGH"
        cited = ["hypo_last3", "delta_mean_bg", "delta_sbp", "last_sbp"]
    elif f["hypo_days_10"] >= 2:
        risk = "MEDIUM"
        cited = ["hypo_days_10", "delta_sbp"]

    nudge = (
        f"Next-day hypo risk {risk}: {int(f['hypo_last3'])} hypo-days in last 3, "
        f"mean BG {f['delta_mean_bg']:+.0f} mg/dL vs week start, SBP {f['delta_sbp']:+.0f}. "
        "Check BG before driving/exercise; keep fast carbs available; review meds with clinician."
    )
    return Draft(risk=risk, cited_features=cited, nudge=nudge, notes="revised from critique")


def verifier(draft: Draft, days: list[dict]) -> dict[str, Any]:
    f = _features(days)
    reasons: list[str] = []
    ok = True

    if draft.risk not in {"LOW", "MEDIUM", "HIGH"}:
        ok = False
        reasons.append("risk not in {LOW,MEDIUM,HIGH}")

    has_bg = any(x.startswith(("hypo", "delta_mean_bg", "last_bg")) for x in draft.cited_features)
    has_bp = any("sbp" in x or x.startswith("delta_sbp") for x in draft.cited_features)
    if not (has_bg and has_bp):
        ok = False
        reasons.append("must cite ≥1 BG-window feature AND ≥1 BP feature")

    must_high = f["hypo_last3"] >= 1 or (f["delta_mean_bg"] < -15 and f["delta_sbp"] > 5)
    if must_high and draft.risk != "HIGH":
        ok = False
        reasons.append(
            f"window requires HIGH (hypo_last3={f['hypo_last3']}, "
            f"dBG={f['delta_mean_bg']:.1f}, dSBP={f['delta_sbp']:.1f})"
        )

    banned = ("insulin dose", "units", "bolus", "increase insulin")
    low_nudge = draft.nudge.lower()
    if any(b in low_nudge for b in banned):
        ok = False
        reasons.append("nudge must not contain insulin dosing advice")

    n = len(draft.nudge)
    if not (40 <= n <= 280):
        ok = False
        reasons.append(f"nudge length {n} not in [40,280]")

    if ok:
        reasons.append("all criteria met")
    return {"pass": ok, "reasons": reasons, "features": f}


def updater(days: list[dict], max_passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: str | None = None
    draft = Draft(risk="LOW", cited_features=[], nudge="", notes="")
    for i in range(max_passes):
        draft = generator(days, critique)
        verdict = verifier(draft, days)
        log.append(
            {
                "pass": i,
                "draft": asdict(draft),
                "verdict": {k: v for k, v in verdict.items() if k != "features"},
                "features": verdict["features"],
            }
        )
        if verdict["pass"]:
            break
        critique = "; ".join(verdict["reasons"])
    return log


def main() -> None:
    log = updater(SAMPLE["days"])
    out_dir = Path(__file__).resolve().parent
    (out_dir / "run_log.json").write_text(json.dumps(log, indent=2))
    first = log[0]["draft"]
    last = log[-1]["draft"]
    smoke = (
        f"BEFORE pass0: risk={first['risk']} cited={first['cited_features']}\n"
        f"AFTER  pass{log[-1]['pass']}: risk={last['risk']} cited={last['cited_features']} "
        f"PASS={log[-1]['verdict']['pass']}\n"
        f"nudge: {last['nudge']}\n"
    )
    (out_dir / "SMOKE.txt").write_text(smoke)
    print(smoke)
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
