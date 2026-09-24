#!/usr/bin/env python3
"""
Day 2026-09-25 — Time-to-hypoglycemia GVU prototype
Paper seed: Onwuchekwa et al., EMBC 2024 — predict *when* hypo arrives,
not only whether a binary flag fires.

Generator (naive): last CGM point only → "SAFE / no time estimate"
Verifier (explicit):
  PASS iff the draft cites ALL of:
    - time_bin in {0-30, 30-60, 60-120, >120}
    - cgm_slope_mgdl_per_5min
    - heart_rate_bpm
  AND the bin matches the rule below (falsifiable).
Updater: injects missing features and re-bins until PASS or max 3 passes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

HYPO_MGDL = 70.0
MAX_PASSES = 3


@dataclass
class Sample:
    """Synthetic 30-min CGM window (5-min cadence) + contemporaneous HR."""
    cgm: list[float]  # oldest → newest
    hr_bpm: float
    label: str


def slope_per_5min(cgm: list[float]) -> float:
    if len(cgm) < 2:
        return 0.0
    return (cgm[-1] - cgm[0]) / (len(cgm) - 1)


def expected_bin(cgm: list[float], hr_bpm: float) -> str:
    last = cgm[-1]
    sl = slope_per_5min(cgm)
    if last < HYPO_MGDL:
        return "0-30"
    if sl < -0.5:
        minutes = max(0.0, (last - HYPO_MGDL) / abs(sl) * 5.0)
        if hr_bpm >= 90:
            minutes *= 0.7
        if minutes <= 30:
            return "0-30"
        if minutes <= 60:
            return "30-60"
        if minutes <= 120:
            return "60-120"
        return ">120"
    if last >= 90:
        return ">120"
    return "60-120"


def generate(sample: Sample, critique: str | None) -> dict[str, Any]:
    last = sample.cgm[-1]
    if critique is None:
        return {
            "risk": "LOW" if last >= HYPO_MGDL else "HIGH",
            "time_bin": None,
            "cited": ["last_cgm"],
            "last_cgm": last,
            "note": "Draft from last CGM only; no time-to-event.",
        }
    sl = slope_per_5min(sample.cgm)
    bin_ = expected_bin(sample.cgm, sample.hr_bpm)
    return {
        "risk": "HIGH" if bin_ in {"0-30", "30-60"} else "WATCH",
        "time_bin": bin_,
        "cited": ["time_bin", "cgm_slope_mgdl_per_5min", "heart_rate_bpm"],
        "last_cgm": last,
        "cgm_slope_mgdl_per_5min": round(sl, 3),
        "heart_rate_bpm": sample.hr_bpm,
        "note": f"Revised after critique: {critique[:80]}",
    }


def verify(draft: dict[str, Any], sample: Sample) -> tuple[bool, str]:
    required = {"time_bin", "cgm_slope_mgdl_per_5min", "heart_rate_bpm"}
    cited = set(draft.get("cited") or [])
    missing = required - cited
    want = expected_bin(sample.cgm, sample.hr_bpm)
    got = draft.get("time_bin")
    if missing:
        return False, f"FAIL: missing citations {sorted(missing)}; expected bin={want}"
    if got != want:
        return False, f"FAIL: time_bin={got} != expected {want} given slope+HR"
    return True, f"PASS: time_bin={got} matches slope+HR rule; citations complete"


def run_gvu(sample: Sample) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: str | None = None
    for i in range(1, MAX_PASSES + 1):
        draft = generate(sample, critique)
        ok, reason = verify(draft, sample)
        log.append({"pass": i, "ok": ok, "reason": reason, "draft": draft})
        if ok:
            break
        critique = reason
    return log


SAMPLE = Sample(
    cgm=[118, 112, 104, 95, 88, 81],
    hr_bpm=96.0,
    label="descending + high HR",
)


def main() -> None:
    log = run_gvu(SAMPLE)
    print("=== SAMPLE ===")
    print(json.dumps(asdict(SAMPLE), indent=2))
    print("=== GVU PASSES ===")
    print(json.dumps(log, indent=2))
    before = log[0]["draft"]
    after = log[-1]["draft"]
    print("\nBEFORE:", json.dumps(before))
    print("AFTER :", json.dumps(after))
    print("FINAL :", log[-1]["reason"])
    out = Path(__file__).resolve().parent
    (out / "run_log.json").write_text(json.dumps(log, indent=2))
    smoke = (
        f"before_time_bin={before.get('time_bin')} "
        f"after_time_bin={after.get('time_bin')} "
        f"final={log[-1]['ok']}\n"
    )
    (out / "SMOKE.txt").write_text(smoke)


if __name__ == "__main__":
    main()
