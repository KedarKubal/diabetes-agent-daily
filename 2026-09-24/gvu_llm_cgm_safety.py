#!/usr/bin/env python3
"""Day 2026-09-24 GVU: conversational CGM safety answer with falsifiable verifier.

Generator drafts a patient-facing overnight-safety reply from a CGM window.
Verifier requires explicit citations (TBR, descending-run, last value) and
forbids SAFE when TBR>4% or any reading <70.
Updater feeds the critique back for 3 passes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


SAMPLE = {
    "question": "Am I safe overnight?",
    "cgm_mgdl": [118, 112, 98, 86, 74, 68, 64],  # last 3.5h @ 30min
    "interval_min": 30,
}


def features(cgm: list[float]) -> dict[str, Any]:
    n = max(len(cgm), 1)
    below = sum(1 for x in cgm if x < 70)
    tbr = 100.0 * below / n
    run = 0
    for a, b in zip(cgm, cgm[1:]):
        if b < a - 2:
            run += 1
        else:
            run = 0
    return {
        "last": cgm[-1],
        "min": min(cgm),
        "tbr_pct": round(tbr, 1),
        "descending_run": run,
        "n": n,
    }


@dataclass
class Draft:
    label: str
    answer: str
    cited: list[str] = field(default_factory=list)


def generate(sample: dict, critique: str | None) -> Draft:
    f = features(sample["cgm_mgdl"])
    last = f["last"]
    # Naive first pass: last-point only
    if critique is None:
        if last >= 70:
            return Draft(
                "SAFE",
                f"Last reading is {last} mg/dL, so you look safe overnight.",
                cited=["last"],
            )
        return Draft(
            "UNSAFE",
            f"Last reading is {last} mg/dL. Take carbs and recheck.",
            cited=["last"],
        )
    # Revised: use window stats the verifier demanded
    unsafe = f["tbr_pct"] > 4 or f["min"] < 70 or f["descending_run"] >= 3
    label = "UNSAFE" if unsafe else "SAFE"
    answer = (
        f"Overnight risk is {label}. "
        f"Last={f['last']} mg/dL, min={f['min']}, TBR={f['tbr_pct']}%, "
        f"descending_run={f['descending_run']} steps. "
        "Have 15g fast carb available and set a 02:00 check."
    )
    return Draft(label, answer, cited=["last", "tbr_pct", "descending_run", "min"])


REQUIRED = {"last", "tbr_pct", "descending_run"}


def verify(draft: Draft, sample: dict) -> dict[str, Any]:
    f = features(sample["cgm_mgdl"])
    reasons: list[str] = []
    missing = REQUIRED - set(draft.cited)
    if missing:
        reasons.append(f"missing citations: {sorted(missing)}")
    must_unsafe = f["tbr_pct"] > 4 or f["min"] < 70
    if must_unsafe and draft.label == "SAFE":
        reasons.append(
            f"cannot claim SAFE when TBR={f['tbr_pct']}% or min={f['min']}"
        )
    if "tbr_pct" not in draft.answer.lower() and "tbr=" not in draft.answer.lower():
        if "TBR" not in draft.answer:
            reasons.append("answer text must mention TBR")
    ok = not reasons
    return {"pass": ok, "reasons": reasons, "features": f}


def run_gvu(sample: dict, max_passes: int = 3) -> dict[str, Any]:
    log: list[dict[str, Any]] = []
    critique = None
    draft = Draft("SAFE", "", [])
    verdict: dict[str, Any] = {}
    for i in range(1, max_passes + 1):
        draft = generate(sample, critique)
        verdict = verify(draft, sample)
        log.append(
            {
                "pass": i,
                "label": draft.label,
                "answer": draft.answer,
                "cited": draft.cited,
                "verify": verdict,
            }
        )
        if verdict["pass"]:
            break
        critique = "; ".join(verdict["reasons"])
    return {
        "question": sample["question"],
        "final_label": draft.label,
        "final_answer": draft.answer,
        "passed": verdict.get("pass", False),
        "log": log,
    }


if __name__ == "__main__":
    result = run_gvu(SAMPLE)
    print(json.dumps(result, indent=2))
    before = result["log"][0]["answer"]
    after = result["final_answer"]
    print("\n--- SMOKE ---")
    print("BEFORE:", before)
    print("AFTER: ", after)
    print("PASSES:", result["passed"], "label:", result["final_label"])
