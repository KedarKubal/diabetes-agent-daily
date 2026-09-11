#!/usr/bin/env python3
"""Day 2026-09-12 GVU: explainable 60-min hypo/hyper risk flag.

Generator drafts a risk label + top-feature explanation from a short CGM window.
Verifier checks an explicit, numeric success criterion (not vibes).
Updater feeds the critique back for 3 passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SAMPLE = {
    "glucose_mgdl": [118, 108, 99, 91, 84, 79, 74],  # still >70 but steep fall + insulin
    "minutes_apart": 5,
    "recent_insulin_bolus_u": 4.5,
    "hours_since_meal": 3.2,
}


@dataclass
class Draft:
    risk: str  # LOW | MEDIUM | HIGH
    event: str  # hypo | hyper | none
    horizon_min: int
    cited_features: list[str]
    rationale: str
    pass_n: int = 0


@dataclass
class Critique:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def _slope(vals: list[float], dt: float) -> float:
    if len(vals) < 2:
        return 0.0
    return (vals[-1] - vals[0]) / ((len(vals) - 1) * dt)


def generator(sample: dict, critique: Critique | None, prev: Draft | None) -> Draft:
    g = sample["glucose_mgdl"]
    last = g[-1]
    sl = _slope(g, sample["minutes_apart"])
    bolus = sample["recent_insulin_bolus_u"]
    hrs = sample["hours_since_meal"]

    # Naive first pass: last point only
    if prev is None:
        if last < 70:
            risk, event = "HIGH", "hypo"
        elif last > 180:
            risk, event = "HIGH", "hyper"
        else:
            risk, event = "LOW", "none"
        cited = ["last_glucose"]
        rationale = f"Last reading {last} mg/dL."
        return Draft(risk, event, 60, cited, rationale, 1)

    # Later passes incorporate critique: use slope, insulin, meal gap
    predicted_60 = last + sl * 60
    cited = ["last_glucose", "slope_mgdl_per_min"]
    extra = []
    if bolus >= 3:
        cited.append("recent_insulin_bolus")
        extra.append(f"bolus {bolus}U")
    if hrs >= 2.5:
        cited.append("hours_since_meal")
        extra.append(f"{hrs}h since meal")

    if predicted_60 < 70 or (last < 80 and sl < -0.4):
        risk, event = "HIGH", "hypo"
    elif predicted_60 > 250 or last > 220:
        risk, event = "HIGH", "hyper"
    elif last < 90 and sl < 0:
        risk, event = "MEDIUM", "hypo"
    else:
        risk, event = "LOW", "none"

    rationale = (
        f"Last {last} mg/dL, slope {sl:.3f} mg/dL/min, "
        f"~{predicted_60:.0f} at 60 min. " + "; ".join(extra)
    )
    return Draft(risk, event, 60, cited, rationale, prev.pass_n + 1)


def verifier(sample: dict, draft: Draft) -> Critique:
    """Success criterion (falsifiable):
    1) If last glucose < 70 OR (last < 80 AND slope < -0.3 mg/dL/min), risk must be HIGH and event hypo.
    2) cited_features must include every feature used in the rationale tokens:
       last_glucose always; slope if 'slope' in rationale; recent_insulin_bolus if 'bolus' in rationale;
       hours_since_meal if 'since meal' in rationale.
    3) horizon_min must be 60.
    """
    g = sample["glucose_mgdl"]
    last = g[-1]
    sl = _slope(g, sample["minutes_apart"])
    reasons = []

    must_high_hypo = last < 70 or (last < 80 and sl < -0.3)
    if must_high_hypo:
        if draft.risk != "HIGH" or draft.event != "hypo":
            reasons.append(
                f"FAIL risk rule: last={last}, slope={sl:.3f} requires HIGH/hypo, got {draft.risk}/{draft.event}"
            )
    if draft.horizon_min != 60:
        reasons.append(f"FAIL horizon: expected 60, got {draft.horizon_min}")

    required = {"last_glucose"}
    r = draft.rationale.lower()
    if "slope" in r:
        required.add("slope_mgdl_per_min")
    if "bolus" in r:
        required.add("recent_insulin_bolus")
    if "since meal" in r:
        required.add("hours_since_meal")
    missing = required - set(draft.cited_features)
    if missing:
        reasons.append(f"FAIL citation: rationale uses {sorted(required)} but cited {draft.cited_features}; missing {sorted(missing)}")

    if not reasons:
        reasons.append("PASS all numeric rules")
    return Critique(passed=len([x for x in reasons if x.startswith("FAIL")]) == 0, reasons=reasons)


def run_gvu(sample: dict, max_passes: int = 3) -> list[tuple[Draft, Critique]]:
    log = []
    draft = None
    critique = None
    for i in range(max_passes):
        draft = generator(sample, critique, draft)
        critique = verifier(sample, draft)
        log.append((draft, critique))
        if critique.passed:
            break
    return log


def main() -> None:
    print("Sample CGM window:", SAMPLE)
    print()
    for draft, critique in run_gvu(SAMPLE):
        print(f"=== Pass {draft.pass_n} ===")
        print(f"risk={draft.risk} event={draft.event} horizon={draft.horizon_min}")
        print(f"cited={draft.cited_features}")
        print(f"rationale={draft.rationale}")
        print("verifier:", "PASS" if critique.passed else "FAIL")
        for r in critique.reasons:
            print(" -", r)
        print()


if __name__ == "__main__":
    main()
