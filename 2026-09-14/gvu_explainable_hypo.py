#!/usr/bin/env python3
"""Day 2026-09-14 GVU prototype.

Opportunity: Monitoring — self-improving *white-box if-then* 30-min hypo
flag that must cite CGM + heart-rate + steps (De La Cruz et al. 2024
structured grammatical evolution).

Verifier success criterion (falsifiable):
  PASS iff output is HIGH_HYPO_RISK AND the rule text contains all of
  {glucose, slope|delta, heart|hr, step} AND predicted flag matches the
  labeled sample (glucose falling through ~80 with high HR and low steps).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


SAMPLE = {
    "glucose_mgdl": [118, 104, 91, 82],  # 5-min-ish falling series
    "heart_rate": [88, 90, 93, 96],
    "steps_last_20min": 12,
    "label": "HIGH_HYPO_RISK",  # next 30 min expected <70 if trend holds
}


@dataclass
class Draft:
    flag: str
    rule: str
    features_cited: List[str]


def _stats(sample: dict) -> dict:
    g = sample["glucose_mgdl"]
    hr = sample["heart_rate"]
    return {
        "last_g": g[-1],
        "delta_g": g[-1] - g[0],
        "last_hr": hr[-1],
        "steps": sample["steps_last_20min"],
    }


def generate(sample: dict, critique: str | None = None) -> Draft:
    s = _stats(sample)
    # Naive first pass: last glucose only (the "spoilt-child" mind).
    if critique is None:
        return Draft(
            flag="LOW_RISK",
            rule=f"IF last_glucose={s['last_g']} >= 80 THEN LOW_RISK",
            features_cited=["glucose"],
        )
    # Revised: grammatical if-then using CGM + HR + steps.
    flag = "HIGH_HYPO_RISK"
    rule = (
        f"IF last_glucose={s['last_g']} < 90 "
        f"AND delta_glucose={s['delta_g']} <= -20 "
        f"AND heart_rate={s['last_hr']} >= 90 "
        f"AND steps_last_20min={s['steps']} < 50 "
        f"THEN HIGH_HYPO_RISK  # falling CGM + sympathetic HR + inactivity"
    )
    return Draft(
        flag=flag,
        rule=rule,
        features_cited=["glucose", "slope", "heart_rate", "steps"],
    )


def verify(draft: Draft, sample: dict) -> tuple[bool, str]:
    text = (draft.rule + " " + draft.flag).lower()
    needs = ["glucose", "heart", "step"]
    slope_ok = ("slope" in text) or ("delta" in text)
    missing = [n for n in needs if n not in text]
    if not slope_ok:
        missing.append("slope|delta")
    if draft.flag != sample["label"]:
        return False, f"flag {draft.flag} != label {sample['label']}; missing={missing}"
    if missing:
        return False, f"rule is not white-box multimodal; missing={missing}"
    if draft.flag != "HIGH_HYPO_RISK":
        return False, "expected HIGH_HYPO_RISK on this falling+high-HR+low-steps window"
    return True, "PASS: multimodal if-then rule matches labeled 30-min hypo risk"


def run_gvu(sample: dict, max_passes: int = 3) -> list[dict]:
    log: list[dict] = []
    critique = None
    draft = None
    for i in range(1, max_passes + 1):
        draft = generate(sample, critique)
        ok, reason = verify(draft, sample)
        rec = {"pass": i, "ok": ok, "reason": reason, **asdict(draft)}
        log.append(rec)
        if ok:
            break
        critique = reason
    return log


def main() -> None:
    log = run_gvu(SAMPLE)
    out = Path(__file__).with_name("run_log.json")
    out.write_text(json.dumps({"sample": SAMPLE, "passes": log}, indent=2))
    print("=== GVU smoke test 2026-09-14 ===")
    print("BEFORE (pass 1):", log[0]["flag"], "|", log[0]["rule"])
    print("AFTER  (last):  ", log[-1]["flag"], "|", log[-1]["rule"])
    print("passes:", len(log), "final_ok:", log[-1]["ok"])
    print("wrote", out)


if __name__ == "__main__":
    main()
